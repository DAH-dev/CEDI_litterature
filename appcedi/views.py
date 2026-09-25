from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count, Sum, Avg

from .models import *
from .forms import InscriptionForm, ProduitForm, CategorieForm, PointVenteForm, PromotionForm, ArticleBlogForm


# ========== VÉRIFICATION DES DROITS ==========
def est_admin_ou_gestionnaire(user):
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['admin', 'gestionnaire_stock'])


# ========== PAGE D'ACCUEIL ==========
def accueil(request):
    now = timezone.now()
    
    promotions_actives = Promotion.objects.filter(
        date_debut__lte=now,
        date_fin__gte=now
    ).prefetch_related('produits')

    promos_data = []
    for promo in promotions_actives:
        produits_promo = []
        for produit in promo.produits.filter(statut=True):
            if hasattr(promo, 'calculer_prix_reduit'):
                prix_reduit = promo.calculer_prix_reduit(produit.prix)
            else:
                if promo.type_reduction == 'pourcentage':
                    prix_reduit = produit.prix * (1 - promo.valeur_reduction / 100)
                else:
                    prix_reduit = produit.prix - promo.valeur_reduction
            
            produits_promo.append({
                'produit': produit,
                'prix_original': produit.prix,
                'prix_reduit': round(prix_reduit),
            })
            
        if produits_promo:
            promos_data.append({
                'promotion': promo,
                'produits': produits_promo,
            })

    context = {
        'points_de_vente': PointVente.objects.all(),
        'produits_recents': Produit.objects.filter(statut=True).order_by('-id')[:8],
        'promos_data': promos_data,
        'articles_blog': ArticleBlog.objects.filter(statut='publie').order_by('-date_publication')[:3],
    }
    
    return render(request, 'appcedi/accueil.html', context)


# ========== AUTHENTIFICATION ==========
def inscription(request):
    if request.method == 'POST':
        form = InscriptionForm(request.POST) # 👈 Utilisation d'InscriptionForm
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Bienvenue {user.username} ! Votre compte a été créé avec succès.')
            return redirect('accueil')
    else:
        form = InscriptionForm() # 👈 Utilisation d'InscriptionForm
    return render(request, 'appcedi/inscription.html', {'form': form})


def connexion(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bonjour {username} !')
                return redirect('accueil')
    else:
        form = AuthenticationForm()
    return render(request, 'appcedi/connexion.html', {'form': form})


def deconnexion(request):
    logout(request)
    messages.info(request, 'Vous êtes déconnecté.')
    return redirect('accueil')


# ========== PAGES DIVERSES ==========
def a_propos(request):
    points_vente = PointVente.objects.all()
    
    context = {
        'points_vente': points_vente,
        'nb_librairies': points_vente.count(),
        'nb_produits': Produit.objects.filter(statut=True).count(),
        'nb_avis': AvisClient.objects.filter(statut='approuve').count(),
    }
    return render(request, 'appcedi/a_propos.html', context)


# ========== TABLEAU DE BORD ==========
# ========== TABLEAU DE BORD ADMIN (Sécurisé) ==========
@login_required
@user_passes_test(est_admin_ou_gestionnaire, login_url='accueil')
def tableau_de_bord(request):
    context = {
        'total_produits': Produit.objects.count(),
        'total_categories': Categorie.objects.count(),
        'total_points_vente': PointVente.objects.count(),
        'total_promotions': Promotion.objects.count(),
        'total_articles': ArticleBlog.objects.count(),
        'total_commandes': Commande.objects.count(),
        'total_avis': AvisClient.objects.count(),
        'produits_stock_faible': Produit.objects.filter(quantite_stock__lt=3).count(),
        'commandes_attente': Commande.objects.filter(statut='attente_paiement').count(),
        'avis_en_attente': AvisClient.objects.filter(statut='en_attente').count(),
        'questions_en_attente': QuestionConseil.objects.filter(statut='en_attente').count(),
        'temoignages_en_attente': Temoignage.objects.filter(statut='en_attente').count(),
    }
    return render(request, 'appcedi/tableau_de_bord.html', context)

# ========== CRUD PRODUITS ==========
@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def liste_produits(request):
    produits = Produit.objects.all().order_by('-id')
    return render(request, 'appcedi/admin/liste_produits.html', {'produits': produits})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def ajouter_produit(request):
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            produit = form.save()
            
            fichiers = request.FILES.getlist('images_multiples')
            for index, f in enumerate(fichiers):
                if f:
                    Image.objects.create(
                        produit=produit,
                        url_image=f,
                        est_principale=(index == 0)
                    )
            
            messages.success(request, f'Produit "{produit.titre}" ajouté avec succès !')
            return redirect('liste_produits')
    else:
        form = ProduitForm()
    return render(request, 'appcedi/admin/ajouter_produit.html', {'form': form})


def detail_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk, statut=True)
    mon_avis = None
    if request.user.is_authenticated:
        mon_avis = AvisClient.objects.filter(produit=produit, utilisateur=request.user).first()
    images = produit.images.all()
    image_principale = images.filter(est_principale=True).first()
    if not image_principale and images.exists():
        image_principale = images.first()
    autres_images = images.exclude(pk=image_principale.pk) if image_principale else images

    avis_approuves = produit.avis.filter(statut='approuve')
    note_moyenne = produit.moyenne_avis()
    total_avis = avis_approuves.count()

    repartition = {i: avis_approuves.filter(note=i).count() for i in range(1, 6)}

    categories = produit.categories.all()
    produits_similaires = Produit.objects.filter(
        categories__in=categories, statut=True
    ).exclude(pk=produit.pk).distinct()[:4]

    context = {
        'produit': produit,
        'image_principale': image_principale,
        'autres_images': autres_images,
        'avis_approuves': avis_approuves,
        'note_moyenne': note_moyenne,
        'total_avis': total_avis,
        'repartition': repartition,
        'produits_similaires': produits_similaires,
        'points_vente': PointVente.objects.all(),
        'mon_avis': mon_avis,
    }
    return render(request, 'appcedi/detail_produit.html', context)


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def modifier_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES, instance=produit)
        if form.is_valid():
            form.save()
            
            fichiers = request.FILES.getlist('images_multiples')
            for f in fichiers:
                if f:
                    Image.objects.create(
                        produit=produit,
                        url_image=f,
                        est_principale=False
                    )
            
            if not produit.images.filter(est_principale=True).exists():
                premiere = produit.images.first()
                if premiere:
                    premiere.est_principale = True
                    premiere.save()
            
            messages.success(request, f'Produit "{produit.titre}" modifié avec succès !')
            return redirect('liste_produits')
    else:
        form = ProduitForm(instance=produit)
    return render(request, 'appcedi/admin/modifier_produit.html', {'form': form, 'produit': produit})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def supprimer_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        titre = produit.titre
        produit.delete()
        messages.success(request, f'Produit "{titre}" supprimé avec succès !')
        return redirect('liste_produits')
    return render(request, 'appcedi/admin/supprimer_produit.html', {'produit': produit})
from django.core.paginator import Paginator
from django.db.models import Q

import re
from django.db.models import Q
from django.core.paginator import Paginator

def liste_catalogue(request):
    """Affiche tous les produits avec filtres, recherche texte ET prix."""
    produits = Produit.objects.filter(statut=True).order_by('-id')
    categories = Categorie.objects.all()

    # 🔍 Recherche intelligente (texte OU prix)
    q = request.GET.get('q', '').strip()

    if q:
        # Détection d'une plage de prix : "3000-6000" ou "3000 et 6000" ou "entre 3000 et 6000"
        plage_match = re.match(r'^(?:entre\s+)?(\d+)\s*(?:-|et|à)\s*(\d+)\s*(?:fcfa|f)?$', q.lower())

        # Détection d'un prix max : "5000" ou "moins de 5000" ou "<5000" ou "5000 fcfa"
        prix_match = re.match(r'^(?:moins\s+de\s+|<\s*)?(\d+)\s*(?:fcfa|f)?$', q.lower())

        if plage_match:
            min_p = int(plage_match.group(1))
            max_p = int(plage_match.group(2))
            produits = produits.filter(prix__gte=min_p, prix__lte=max_p)
        elif prix_match:
            max_p = int(prix_match.group(1))
            produits = produits.filter(prix__lte=max_p)
        else:
            # Recherche textuelle normale
            produits = produits.filter(
                Q(titre__icontains=q) |
                Q(auteur__icontains=q) |
                Q(editeur__icontains=q) |
                Q(description__icontains=q)
            )

    # 🏷️ Filtre par catégorie
    cat_id = request.GET.get('categorie')
    if cat_id:
        produits = produits.filter(categories__id=cat_id)

    # 💰 Filtre par prix (depuis le menu déroulant)
    prix = request.GET.get('prix')
    if prix == 'bas':
        produits = produits.filter(prix__lt=3000)
    elif prix == 'moyen':
        produits = produits.filter(prix__gte=3000, prix__lte=6000)
    elif prix == 'haut':
        produits = produits.filter(prix__gt=6000)

    # 📚 Filtre par type de produit
    type_produit = request.GET.get('type')
    if type_produit:
        produits = produits.filter(type_produit=type_produit)

    # ⭐ Filtre Édition CEDI
    if request.GET.get('cedi') == '1':
        produits = produits.filter(est_edition_cedi=True)

    # 📄 Pagination
    paginator = Paginator(produits.distinct(), 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'q': q,
        'cat_selectionnee': cat_id,
        'prix_selectionne': prix,
        'type_selectionne': type_produit,
        'cedi_selectionne': request.GET.get('cedi') == '1',
        'total_produits': produits.distinct().count(),
    }
    return render(request, 'appcedi/catalogue.html', context)

def liste_ressources(request):
    """Affiche tous les articles publiés (Enseignements, Vérités, Conseils, Partages)."""
    articles = ArticleBlog.objects.filter(statut='publie').order_by('-date_publication')

    # 🔍 Recherche
    q = request.GET.get('q')
    if q:
        articles = articles.filter(
            Q(titre__icontains=q) | Q(contenu__icontains=q)
        )

    # 📂 Filtre par catégorie
    cat = request.GET.get('categorie')
    if cat:
        articles = articles.filter(categorie_article=cat)

    # 📄 Pagination
    paginator = Paginator(articles, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Liste des catégories disponibles (depuis le modèle)
    categories = ArticleBlog.CATEGORIES

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'q': q,
        'cat_selectionnee': cat,
        'total_articles': articles.count(),
    }
    return render(request, 'appcedi/ressources.html', context)

@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def definir_principale(request, image_id):
    image = get_object_or_404(Image, pk=image_id)
    produit = image.produit
    produit.images.update(est_principale=False)
    image.est_principale = True
    image.save()
    messages.success(request, "Image définie comme principale.")
    return redirect('modifier_produit', pk=produit.pk)


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def supprimer_image(request, image_id):
    image = get_object_or_404(Image, pk=image_id)
    produit = image.produit
    if image.est_principale:
        image.delete()
        nouvelle = produit.images.first()
        if nouvelle:
            nouvelle.est_principale = True
            nouvelle.save()
    else:
        image.delete()
    messages.success(request, "Image supprimée.")
    return redirect('modifier_produit', pk=produit.pk)


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def basculer_statut_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    
    if isinstance(produit.statut, bool):
        produit.statut = not produit.statut
    elif str(produit.statut).lower() == 'actif':
        produit.statut = 'inactif'
    else:
        produit.statut = 'actif'
        
    produit.save()
    messages.success(request, f'Statut du produit "{produit.titre}" mis à jour !')
    return redirect('liste_produits')


# ========== CRUD CATÉGORIES ==========
@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def liste_categories(request):
    categories = Categorie.objects.all()
    return render(request, 'appcedi/admin/liste_categories.html', {'categories': categories})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def ajouter_categorie(request):
    if request.method == 'POST':
        form = CategorieForm(request.POST)
        if form.is_valid():
            categorie = form.save()
            messages.success(request, f'Catégorie "{categorie.nom}" ajoutée avec succès !')
            return redirect('liste_categories')
    else:
        form = CategorieForm()
    return render(request, 'appcedi/admin/ajouter_categorie.html', {'form': form})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def modifier_categorie(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == 'POST':
        form = CategorieForm(request.POST, instance=categorie)
        if form.is_valid():
            form.save()
            messages.success(request, f'Catégorie "{categorie.nom}" modifiée avec succès !')
            return redirect('liste_categories')
    else:
        form = CategorieForm(instance=categorie)
    return render(request, 'appcedi/admin/modifier_categorie.html', {'form': form, 'categorie': categorie})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def supprimer_categorie(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == 'POST':
        nom = categorie.nom
        categorie.delete()
        messages.success(request, f'Catégorie "{nom}" supprimée avec succès !')
        return redirect('liste_categories')
    return render(request, 'appcedi/admin/supprimer_categorie.html', {'categorie': categorie})


# ========== CRUD POINTS DE VENTE ==========
@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def liste_points_vente(request):
    points = PointVente.objects.all()
    return render(request, 'appcedi/admin/liste_points_vente.html', {'points': points})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def ajouter_point_vente(request):
    if request.method == 'POST':
        form = PointVenteForm(request.POST, request.FILES)
        if form.is_valid():
            point = form.save()
            messages.success(request, f'Point de vente "{point.nom}" ajouté avec succès !')
            return redirect('liste_points_vente')
    else:
        form = PointVenteForm()
    return render(request, 'appcedi/admin/ajouter_point_vente.html', {'form': form})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def modifier_point_vente(request, pk):
    point = get_object_or_404(PointVente, pk=pk)
    if request.method == 'POST':
        form = PointVenteForm(request.POST, request.FILES, instance=point)
        if form.is_valid():
            form.save()
            messages.success(request, f'Point de vente "{point.nom}" modifié avec succès !')
            return redirect('liste_points_vente')
    else:
        form = PointVenteForm(instance=point)
    return render(request, 'appcedi/admin/modifier_point_vente.html', {'form': form, 'point': point})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def supprimer_point_vente(request, pk):
    point = get_object_or_404(PointVente, pk=pk)
    if request.method == 'POST':
        nom = point.nom
        point.delete()
        messages.success(request, f'Point de vente "{nom}" supprimé avec succès !')
        return redirect('liste_points_vente')
    return render(request, 'appcedi/admin/supprimer_point_vente.html', {'point': point})


# ========== CRUD PROMOTIONS ==========
@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def liste_promotions(request):
    maintenant = timezone.now()
    promotions = Promotion.objects.all().order_by('-date_debut')
    
    promos_enrichies = []
    for promo in promotions:
        if promo.date_fin < maintenant:
            statut = 'expiree'
            statut_libelle = 'Expirée'
        elif promo.date_debut > maintenant:
            statut = 'a_venir'
            statut_libelle = 'À venir'
        else:
            statut = 'en_cours'
            statut_libelle = 'En cours'
            
        promos_enrichies.append({
            'promo': promo,
            'statut': statut,
            'statut_libelle': statut_libelle,
        })

    context = {
        'promos_enrichies': promos_enrichies,
        'maintenant': maintenant,
    }
    return render(request, 'appcedi/admin/liste_promotions.html', context)


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def basculer_statut_promotion(request, promo_id):
    promo = get_object_or_404(Promotion, id=promo_id)
    promo.actif = not promo.actif
    promo.save()
    return redirect('liste_promotions')


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def ajouter_promotion(request):
    if request.method == 'POST':
        form = PromotionForm(request.POST)
        if form.is_valid():
            promo = form.save()
            messages.success(request, f'Promotion "{promo.titre}" ajoutée avec succès !')
            return redirect('liste_promotions')
    else:
        form = PromotionForm()
    return render(request, 'appcedi/admin/ajouter_promotion.html', {'form': form})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def modifier_promotion(request, pk):
    promo = get_object_or_404(Promotion, pk=pk)
    if request.method == 'POST':
        form = PromotionForm(request.POST, instance=promo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Promotion "{promo.titre}" modifiée avec succès !')
            return redirect('liste_promotions')
    else:
        form = PromotionForm(instance=promo)
    return render(request, 'appcedi/admin/modifier_promotion.html', {'form': form, 'promo': promo})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def supprimer_promotion(request, pk):
    promo = get_object_or_404(Promotion, pk=pk)
    if request.method == 'POST':
        titre = promo.titre
        promo.delete()
        messages.success(request, f'Promotion "{titre}" supprimée avec succès !')
        return redirect('liste_promotions')
    return render(request, 'appcedi/admin/supprimer_promotion.html', {'promo': promo})


# ========== CRUD ARTICLES DE BLOG ==========
@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def liste_articles(request):
    articles = ArticleBlog.objects.all().order_by('-date_publication')
    return render(request, 'appcedi/admin/liste_articles.html', {'articles': articles})

from django.shortcuts import render, redirect, get_object_or_404
from .models import Produit, Panier, ArticlePanier, ListeSouhaits, AvisProduit, Commande, LigneCommande

# ==========================================
# 1. GESTION DU PANIER CLIENT
# ==========================================

def voir_panier(request):
    """Affiche le contenu du panier de l'utilisateur."""
    if request.user.is_authenticated:
        panier, created = Panier.objects.get_or_create(utilisateur=request.user)
    else:
        # Pour les utilisateurs non connectés via la session
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        panier, created = Panier.objects.get_or_create(session_id=session_key)

    articles = panier.articles.all()
    total = sum(article.produit.prix * article.quantite for article in articles)
    
    context = {
        'panier': panier,
        'articles': articles,
        'total': total,
    }
    return render(request, 'appcedi/panier/panier_detail.html', context)


def ajouter_au_panier(request, produit_id):
    """Ajoute un produit au panier (gestion connectés & anonymes)."""
    # Correction de actif=True -> statut=True
    produit = get_object_or_404(Produit, id=produit_id, statut=True)
    
    if request.user.is_authenticated:
        panier, _ = Panier.objects.get_or_create(utilisateur=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        panier, _ = Panier.objects.get_or_create(session_id=session_key)

    quantite = int(request.POST.get('quantite', 1))
    
    # Vérification ou création de l'article dans le panier
    article, created = ArticlePanier.objects.get_or_create(panier=panier, produit=produit)
    if not created:
        article.quantite += quantite
    else:
        article.quantite = quantite
    article.save()

    messages.success(request, f"{produit.titre} a été ajouté à votre panier.")
    return redirect('voir_panier')


def modifier_quantite_panier(request, article_id):
    """Met à jour la quantité d'un article dans le panier."""
    article = get_object_or_404(ArticlePanier, id=article_id)
    action = request.POST.get('action') # 'augmenter' ou 'reduire'

    if action == 'augmenter':
        article.quantite += 1
        article.save()
    elif action == 'reduire':
        if article.quantite > 1:
            article.quantite -= 1
            article.save()
        else:
            article.delete()

    return redirect('voir_panier')


def supprimer_du_panier(request, article_id):
    """Supprime un article du panier."""
    article = get_object_or_404(ArticlePanier, id=article_id)
    article.delete()
    messages.info(request, "Article retiré du panier.")
    return redirect('voir_panier')


# ==========================================
# 2. LISTE DE SOUHAITS (WISHLIST)
# ==========================================

@login_required
def voir_liste_souhaits(request):
    """Affiche tous les produits enregistrés par l'utilisateur."""
    items = ListeSouhaits.objects.filter(utilisateur=request.user).select_related('produit')
    return render(request, 'appcedi/panier/liste_souhaits.html', {'items': items})

@login_required
def basculer_liste_souhaits(request, produit_id):
    """Ajoute ou retire un produit de la liste de souhaits."""
    produit = get_object_or_404(Produit, id=produit_id)
    soufait, created = ListeSouhaits.objects.get_or_create(
        utilisateur=request.user, 
        produit=produit
    )
    
    if not created:
        # Si le produit était déjà dans la liste, on le supprime
        soufait.delete()
        
    return redirect('voir_liste_souhaits')
@login_required
def espace_client(request):
    # Onglet actif
    tab = request.GET.get('tab', 'profil')

    # 1. Historique des commandes (champ = client, pas utilisateur)
    commandes = Commande.objects.filter(client=request.user).order_by('-date_commande')

    # 2. Liste de souhaits
    souhaits = ListeSouhaits.objects.filter(utilisateur=request.user).select_related('produit')

    # 3. Panier (related_name = articles)
    panier_items = []
    panier_total = 0
    try:
        panier = Panier.objects.get(utilisateur=request.user)
        panier_items = panier.articles.select_related('produit').all()
        panier_total = sum(item.produit.prix * item.quantite for item in panier_items)
    except Panier.DoesNotExist:
        pass

    context = {
        'active_tab': tab,
        'commandes': commandes,
        'souhaits': souhaits,
        'panier_items': panier_items,
        'panier_total': panier_total,
    }
    return render(request, 'appcedi/espace_client.html', context)


# ==========================================
# Soumettre un avis produit (sur la fiche produit)
# ==========================================


@login_required
def ajouter_avis_produit(request, produit_id):
    if request.method == 'POST':
        produit = get_object_or_404(Produit, pk=produit_id)
        note = request.POST.get('note')
        commentaire = request.POST.get('commentaire', '')

        AvisClient.objects.update_or_create(
            produit=produit,
            utilisateur=request.user,
            defaults={
                'note': note,
                'commentaire': commentaire,
                'statut': 'en_attente',  # modération par l'admin
            }
        )
        messages.success(request, "Merci ! Votre avis sera publié après modération.")
    return redirect('detail_produit', pk=produit_id)


# ==========================================
# 4. VALIDER LA COMMANDE (CHECKOUT)
# ==========================================

import uuid
from django.utils import timezone

@login_required
def valider_commande(request):
    """Transforme le contenu du panier en une commande."""
    try:
        panier = Panier.objects.get(utilisateur=request.user)
        articles = panier.articles.select_related('produit').all()
        if not articles.exists():
            messages.warning(request, "Votre panier est vide.")
            return redirect('voir_panier')
    except Panier.DoesNotExist:
        messages.warning(request, "Votre panier est vide.")
        return redirect('voir_panier')

    if request.method == 'POST':
        adresse_livraison = request.POST.get('adresse_livraison', '')
        telephone = request.POST.get('telephone', '')
        mode = request.POST.get('mode_livraison', 'retrait')  # 'retrait' ou 'livraison'

        # Calcul du total
        total = sum(item.produit.prix * item.quantite for item in articles)

        # Référence unique
        reference = f"CMD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # Création de la commande (noms de champs corrigés)
        commande = Commande.objects.create(
            client=request.user,
            statut='attente_paiement',
            mode_livraison=mode,
            adresse_livraison=adresse_livraison,
            frais_port=0,
            montant_total=total,
            reference_commande=reference,
        )

        # Lignes de commande (champ prix_unitaire_au_moment)
        for item in articles:
            LigneCommande.objects.create(
                commande=commande,
                produit=item.produit,
                quantite=item.quantite,
                prix_unitaire_au_moment=item.produit.prix,
            )

        # Vider le panier
        articles.delete()

        messages.success(request, f"Votre commande {reference} a été enregistrée avec succès !")
        return redirect('espace_client')

    total = sum(item.produit.prix * item.quantite for item in articles)
    return render(request, 'appcedi/panier/checkout.html', {'articles': articles, 'total': total})


# Soumettre un témoignage général sur le site (ex: page d'accueil ou à propos)
@login_required
def ajouter_temoignage_site(request):
    if request.method == 'POST':
        contenu = request.POST.get('commentaire') or request.POST.get('contenu')
        if contenu:
            Temoignage.objects.create(
                utilisateur=request.user,
                contenu=contenu,
                statut='en_attente',
            )
            messages.success(request, "Merci ! Votre témoignage a été transmis à l'équipe.")
    return redirect(request.META.get('HTTP_REFERER', 'accueil'))

# ========== TÉMOIGNAGES (ADMIN) ==========
@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def liste_temoignages(request):
    temoignages = Temoignage.objects.all().order_by('-date_creation')
    return render(request, 'appcedi/admin/liste_temoignages.html', {'temoignages': temoignages})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def detail_temoignage(request, pk):
    temoignage = get_object_or_404(Temoignage, pk=pk)
    return render(request, 'appcedi/admin/detail_temoignage.html', {'temoignage': temoignage})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def approuver_temoignage(request, pk):
    temoignage = get_object_or_404(Temoignage, pk=pk)
    temoignage.statut = 'approuve'
    temoignage.save()
    messages.success(request, "Témoignage approuvé avec succès !")
    return redirect('liste_temoignages')


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def rejeter_temoignage(request, pk):
    temoignage = get_object_or_404(Temoignage, pk=pk)
    temoignage.statut = 'rejete'
    temoignage.save()
    messages.success(request, "Témoignage rejeté.")
    return redirect('liste_temoignages')


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def changer_statut_temoignage(request, pk):
    temoignage = get_object_or_404(Temoignage, pk=pk)
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut in dict(Temoignage.STATUT_CHOICES).keys():
            temoignage.statut = nouveau_statut
            temoignage.save()
            messages.success(request, f'Statut mis à jour : {temoignage.get_statut_display()}')
        return redirect('liste_temoignages')
    return render(request, 'appcedi/admin/changer_statut_temoignage.html', {'temoignage': temoignage})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def supprimer_temoignage(request, pk):
    temoignage = get_object_or_404(Temoignage, pk=pk)
    if request.method == 'POST':
        temoignage.delete()
        messages.success(request, "Témoignage supprimé.")
        return redirect('liste_temoignages')
    return render(request, 'appcedi/admin/supprimer_temoignage.html', {'temoignage': temoignage})


# ========== TÉMOIGNAGES (PUBLIC) ==========
def liste_temoignages_publics(request):
    """Affiche tous les témoignages approuvés."""
    temoignages = Temoignage.objects.filter(statut='approuve').order_by('-date_creation')
    return render(request, 'appcedi/temoignages.html', {'temoignages': temoignages})


@login_required
def soumettre_temoignage(request):
    """Un utilisateur connecté soumet un témoignage."""
    if request.method == 'POST':
        contenu = request.POST.get('contenu', '').strip()
        if contenu:
            Temoignage.objects.create(
                utilisateur=request.user,
                contenu=contenu,
                statut='en_attente',
            )
            messages.success(request, "Merci ! Votre témoignage sera publié après modération.")
        else:
            messages.error(request, "Merci d'écrire votre témoignage avant d'envoyer.")
    return redirect(request.META.get('HTTP_REFERER', 'accueil'))



@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def ajouter_article(request):
    if request.method == 'POST':
        form = ArticleBlogForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            article.auteur = request.user
            article.save()
            messages.success(request, f'Article "{article.titre}" publié avec succès !')
            return redirect('liste_articles')
    else:
        form = ArticleBlogForm()
    return render(request, 'appcedi/admin/ajouter_article.html', {'form': form})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def modifier_article(request, pk):
    article = get_object_or_404(ArticleBlog, pk=pk)
    if request.method == 'POST':
        form = ArticleBlogForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            messages.success(request, f'Article "{article.titre}" modifié avec succès !')
            return redirect('liste_articles')
    else:
        form = ArticleBlogForm(instance=article)
    return render(request, 'appcedi/admin/modifier_article.html', {'form': form, 'article': article})


def article_detail(request, pk):
    article = get_object_or_404(ArticleBlog, pk=pk, statut='publie')
    articles_similaires = ArticleBlog.objects.filter(
        categorie_article=article.categorie_article,
        statut='publie'
    ).exclude(id=article.id)[:3]
    
    return render(request, 'appcedi/article_detail.html', {
        'article': article,
        'articles_similaires': articles_similaires,
    })


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def supprimer_article(request, pk):
    article = get_object_or_404(ArticleBlog, pk=pk)
    if request.method == 'POST':
        titre = article.titre
        article.delete()
        messages.success(request, f'Article "{titre}" supprimé avec succès !')
        return redirect('liste_articles')
    return render(request, 'appcedi/admin/supprimer_article.html', {'article': article})


# ========== CRUD AVIS CLIENTS (MODÉRATION) ==========
@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def liste_avis(request):
    avis = AvisClient.objects.all().order_by('-date_creation')
    return render(request, 'appcedi/admin/liste_avis.html', {'avis': avis})

@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def detail_avis(request, pk):
    """Affiche le détail d'un avis."""
    avis = get_object_or_404(AvisClient, pk=pk)
    return render(request, 'appcedi/admin/detail_avis.html', {'avis': avis})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def changer_statut_avis(request, pk):
    """Change le statut d'un avis (approuvé, rejeté, en attente)."""
    avis = get_object_or_404(AvisClient, pk=pk)
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut in dict(AvisClient.STATUT_CHOICES).keys():
            avis.statut = nouveau_statut
            avis.save()
            messages.success(request, f'Statut mis à jour : {avis.get_statut_display()}')
        return redirect('liste_avis')
    return render(request, 'appcedi/admin/changer_statut_avis.html', {'avis': avis})

@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def approuver_avis(request, pk):
    avis = get_object_or_404(AvisClient, pk=pk)
    avis.statut = 'approuve'
    avis.save()
    messages.success(request, 'Avis approuvé avec succès !')
    return redirect('liste_avis')


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def rejeter_avis(request, pk):
    avis = get_object_or_404(AvisClient, pk=pk)
    avis.statut = 'rejete'
    avis.save()
    messages.success(request, 'Avis rejeté.')
    return redirect('liste_avis')


# ========== CRUD QUESTIONS CONSEILS ==========
@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def liste_questions(request):
    questions = QuestionConseil.objects.all().order_by('-date_question')
    return render(request, 'appcedi/admin/liste_questions.html', {'questions': questions})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def repondre_question(request, pk):
    question = get_object_or_404(QuestionConseil, pk=pk)
    if request.method == 'POST':
        question.statut = 'repondu'
        question.save()
        messages.success(request, 'Question marquée comme répondue.')
        return redirect('liste_questions')
    return render(request, 'appcedi/admin/repondre_question.html', {'question': question})


# ========== CRUD COMMANDES ==========
@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def liste_commandes(request):
    commandes = Commande.objects.all().order_by('-date_commande')
    return render(request, 'appcedi/admin/liste_commandes.html', {'commandes': commandes})


@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def changer_statut_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut in dict(Commande.STATUTS).keys():
            commande.statut = nouveau_statut
            commande.save()
            messages.success(request, f'Statut de la commande mis à jour : {commande.get_statut_display()}')
        return redirect('liste_commandes')
    return render(request, 'appcedi/admin/changer_statut_commande.html', {'commande': commande})

@login_required
def ajouter_temoignage_site(request):
    if request.method == 'POST':
        contenu = request.POST.get('commentaire') or request.POST.get('contenu')
        if contenu:
            Temoignage.objects.create(
                utilisateur=request.user,
                contenu=contenu,
                statut='en_attente',
            )
            messages.success(request, "Merci ! Votre témoignage a été transmis à l'équipe.")
    return redirect(request.META.get('HTTP_REFERER', 'accueil'))