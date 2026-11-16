from datetime import datetime
import re
import uuid
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db.models import Count, Sum, Avg, Q
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django import forms
from django.contrib.auth.models import User

from .models import *
from .forms import (
    ModifierProfilForm, InscriptionForm, ProduitForm, CategorieForm, 
    PointVenteForm, PromotionForm, ArticleBlogForm
)


# ========== VÉRIFICATION DES DROITS (RÔLES) ==========
def est_admin(user):
    """Superadmin ou Admin"""
    return user.is_superuser or (hasattr(user, 'profil') and user.profil.role == 'admin')

def est_gestionnaire_stock(user):
    """Admin, Superadmin ou Gestionnaire de stock"""
    return est_admin(user) or (hasattr(user, 'profil') and user.profil.role == 'gestionnaire_stock')

def est_conseiller(user):
    """Admin, Superadmin ou Conseiller"""
    return est_admin(user) or (hasattr(user, 'profil') and user.profil.role == 'conseiller')
def est_staff(user):
    """Vérifie si l'utilisateur a un rôle d'administration (peu importe lequel)."""
    if user.is_superuser:
        return True
    if hasattr(user, 'profil') and user.profil.role in ['admin', 'gestionnaire_stock', 'conseiller']:
        return True
    return False

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
        'produits_recents': Produit.objects.filter(statut=True).order_by('-id')[:40],
        'promos_data': promos_data,
        'articles_blog': ArticleBlog.objects.filter(statut='publie').order_by('-date_publication')[:3],
    }
    
    return render(request, 'appcedi/accueil.html', context)


# ========== AUTHENTIFICATION ==========
def inscription(request):
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Bienvenue {user.username} ! Votre compte a été créé avec succès.')
            return redirect('accueil')
    else:
        form = InscriptionForm()
    return render(request, 'appcedi/inscription.html', {'form': form})


def connexion(request):
    if request.method == 'POST':
        identifiant = request.POST.get('username')
        password = request.POST.get('password')
        
        user_obj = User.objects.filter(Q(username=identifiant) | Q(email=identifiant)).first()
        
        if user_obj:
            user = authenticate(request, username=user_obj.username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bonjour {user.username} !')
                
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('accueil')
        
        messages.error(request, "Nom d'utilisateur/Email ou mot de passe incorrect.")
        
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
@login_required
@user_passes_test(est_staff, login_url='accueil') # 👈 On utilise est_staff au lieu de est_admin
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


# ========== CRUD PRODUITS (Gestionnaire de stock) ==========
@login_required
@user_passes_test(est_gestionnaire_stock)
def liste_produits(request):
    query = request.GET.get('q', '').strip()
    produits = Produit.objects.all().order_by('-id')

    if query:
        produits = produits.filter(
            Q(titre__icontains=query) | Q(auteur__icontains=query) | Q(isbn__icontains=query)
        )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('appcedi/admin/partials/_produits_rows.html', {'produits': produits})
        return JsonResponse({'html': html})

    return render(request, 'appcedi/admin/liste_produits.html', {'produits': produits})

@login_required
@user_passes_test(est_gestionnaire_stock)
def ajouter_produit(request):
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            produit = form.save()
            fichiers = request.FILES.getlist('images_multiples')
            for index, f in enumerate(fichiers):
                if f:
                    Image.objects.create(produit=produit, url_image=f, est_principale=(index == 0))
            
            messages.success(request, f'Produit "{produit.titre}" ajouté avec succès !')
            return redirect('liste_produits')
    else:
        form = ProduitForm()
    return render(request, 'appcedi/admin/ajouter_produit.html', {'form': form})

def detail_produit(request, pk):
    # 1. On récupère le produit
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

    # 👇 2. LE CALCUL DE LA PROMOTION SE FAIT ICI (Après avoir défini le produit) 👇
    prix_actuel = produit.prix
    prix_original = None
    promotion_active = None
    
    from django.utils import timezone
    now = timezone.now()
    
    promotions = ProduitPromotion.objects.filter(
        produit=produit,
        promotion__date_debut__lte=now,
        promotion__date_fin__gte=now,
        promotion__actif=True
    )
    
    if promotions.exists():
        promotion_active = promotions.first().promotion
        if promotion_active.type_reduction == 'pourcentage':
            prix_actuel = produit.prix * (1 - promotion_active.valeur_reduction / 100)
        else:
            prix_actuel = produit.prix - promotion_active.valeur_reduction
        prix_actuel = int(round(prix_actuel))
        prix_original = produit.prix
    # 👆 FIN DU CALCUL DE LA PROMOTION 👆

    # 3. On envoie tout au template
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
        'prix_actuel': prix_actuel,        # 👈 Ajouté
        'prix_original': prix_original,    # 👈 Ajouté
        'promotion_active': promotion_active, # 👈 Ajouté
    }
    return render(request, 'appcedi/detail_produit.html', context)
@login_required
@user_passes_test(est_gestionnaire_stock)
def modifier_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES, instance=produit)
        if form.is_valid():
            form.save()
            fichiers = request.FILES.getlist('images_multiples')
            for f in fichiers:
                if f:
                    Image.objects.create(produit=produit, url_image=f, est_principale=False)
            
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
@user_passes_test(est_gestionnaire_stock)
def supprimer_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        titre = produit.titre
        produit.delete()
        messages.success(request, f'Produit "{titre}" supprimé avec succès !')
        return redirect('liste_produits')
    return render(request, 'appcedi/admin/supprimer_produit.html', {'produit': produit})

@login_required
@user_passes_test(est_gestionnaire_stock)
def actions_produits_bulk(request):
    if request.method == 'POST':
        produit_ids = request.POST.getlist('produit_ids')
        action = request.POST.get('action')
        
        if not produit_ids:
            messages.warning(request, "Veuillez sélectionner au moins un produit.")
            return redirect('liste_produits')

        produits = Produit.objects.filter(id__in=produit_ids)
        count = produits.count()

        if action == 'activate':
            produits.update(statut=True)
        elif action == 'deactivate':
            produits.update(statut=False)
        elif action == 'set_cedi':
            produits.update(est_edition_cedi=True)
        elif action == 'delete':
            produits.delete()
        
        messages.success(request, f"Action effectuée sur {count} produit(s).")
    return redirect('liste_produits')

def liste_catalogue(request):
    produits = Produit.objects.filter(statut=True).order_by('-id')
    categories = Categorie.objects.all()
    q = request.GET.get('q', '').strip()

    if q:
        plage_match = re.match(r'^(?:entre\s+)?(\d+)\s*(?:-|et|à)\s*(\d+)\s*(?:fcfa|f)?$', q.lower())
        prix_match = re.match(r'^(?:moins\s+de\s+|<\s*)?(\d+)\s*(?:fcfa|f)?$', q.lower())

        if plage_match:
            produits = produits.filter(prix__gte=int(plage_match.group(1)), prix__lte=int(plage_match.group(2)))
        elif prix_match:
            produits = produits.filter(prix__lte=int(prix_match.group(1)))
        else:
            produits = produits.filter(Q(titre__icontains=q) | Q(auteur__icontains=q) | Q(editeur__icontains=q) | Q(description__icontains=q))

    cat_id = request.GET.get('categorie')
    if cat_id: produits = produits.filter(categories__id=cat_id)

    prix = request.GET.get('prix')
    if prix == 'bas': produits = produits.filter(prix__lt=3000)
    elif prix == 'moyen': produits = produits.filter(prix__gte=3000, prix__lte=6000)
    elif prix == 'haut': produits = produits.filter(prix__gt=6000)

    type_produit = request.GET.get('type')
    if type_produit: produits = produits.filter(type_produit=type_produit)
    if request.GET.get('cedi') == '1': produits = produits.filter(est_edition_cedi=True)

    paginator = Paginator(produits.distinct(), 40)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj, 'categories': categories, 'q': q,
        'cat_selectionnee': cat_id, 'prix_selectionne': prix,
        'type_selectionne': type_produit, 'cedi_selectionne': request.GET.get('cedi') == '1',
        'total_produits': produits.distinct().count(),
    }
    return render(request, 'appcedi/catalogue.html', context)

def liste_ressources(request):
    articles = ArticleBlog.objects.filter(statut='publie').order_by('-date_publication')
    q = request.GET.get('q')
    if q: articles = articles.filter(Q(titre__icontains=q) | Q(contenu__icontains=q))
    cat = request.GET.get('categorie')
    if cat: articles = articles.filter(categorie_article=cat)

    paginator = Paginator(articles, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj, 'categories': ArticleBlog.CATEGORIES, 
        'q': q, 'cat_selectionnee': cat, 'total_articles': articles.count(),
    }
    return render(request, 'appcedi/ressources.html', context)

@login_required
@user_passes_test(est_gestionnaire_stock)
def definir_principale(request, image_id):
    image = get_object_or_404(Image, pk=image_id)
    produit = image.produit
    produit.images.update(est_principale=False)
    image.est_principale = True
    image.save()
    messages.success(request, "Image définie comme principale.")
    return redirect('modifier_produit', pk=produit.pk)

@login_required
@user_passes_test(est_gestionnaire_stock)
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
@user_passes_test(est_gestionnaire_stock)
def basculer_statut_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    produit.statut = not produit.statut
    produit.save()
    messages.success(request, f'Statut du produit "{produit.titre}" mis à jour !')
    return redirect('liste_produits')


# ========== CRUD CATÉGORIES (Gestionnaire de stock) ==========
@login_required
@user_passes_test(est_gestionnaire_stock)
def liste_categories(request):
    categories = Categorie.objects.all()
    return render(request, 'appcedi/admin/liste_categories.html', {'categories': categories})

@login_required
@user_passes_test(est_gestionnaire_stock)
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
@user_passes_test(est_gestionnaire_stock)
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
@user_passes_test(est_gestionnaire_stock)
def supprimer_categorie(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == 'POST':
        nom = categorie.nom
        categorie.delete()
        messages.success(request, f'Catégorie "{nom}" supprimée avec succès !')
        return redirect('liste_categories')
    return render(request, 'appcedi/admin/supprimer_categorie.html', {'categorie': categorie})

@login_required
@user_passes_test(est_gestionnaire_stock)
def actions_categories_bulk(request):
    if request.method == 'POST':
        categorie_ids = request.POST.getlist('categorie_ids')
        if not categorie_ids:
            messages.warning(request, "Veuillez sélectionner au moins une catégorie.")
            return redirect('liste_categories')
        Categorie.objects.filter(id__in=categorie_ids).delete()
        messages.success(request, f"Catégorie(s) supprimée(s) avec succès.")
    return redirect('liste_categories')


# ========== CRUD POINTS DE VENTE (Gestionnaire de stock) ==========
@login_required
@user_passes_test(est_gestionnaire_stock)
def liste_points_vente(request):
    points = PointVente.objects.all()
    return render(request, 'appcedi/admin/liste_points_vente.html', {'points': points})

@login_required
@user_passes_test(est_gestionnaire_stock)
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
@user_passes_test(est_gestionnaire_stock)
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
@user_passes_test(est_gestionnaire_stock)
def supprimer_point_vente(request, pk):
    point = get_object_or_404(PointVente, pk=pk)
    if request.method == 'POST':
        nom = point.nom
        point.delete()
        messages.success(request, f'Point de vente "{nom}" supprimé avec succès !')
        return redirect('liste_points_vente')
    return render(request, 'appcedi/admin/supprimer_point_vente.html', {'point': point})


# ========== CRUD PROMOTIONS (Gestionnaire de stock) ==========
@login_required
@user_passes_test(est_gestionnaire_stock)
def liste_promotions(request):
    maintenant = timezone.now()
    promotions = Promotion.objects.all().order_by('-date_debut')
    promos_enrichies = []
    
    for promo in promotions:
        if promo.date_fin < maintenant:
            statut, libelle = 'expiree', 'Expirée'
        elif promo.date_debut > maintenant:
            statut, libelle = 'a_venir', 'À venir'
        else:
            statut, libelle = 'en_cours', 'En cours'
            
        promos_enrichies.append({'promo': promo, 'statut': statut, 'statut_libelle': libelle})

    return render(request, 'appcedi/admin/liste_promotions.html', {'promos_enrichies': promos_enrichies, 'maintenant': maintenant})

@login_required
@user_passes_test(est_gestionnaire_stock)
def basculer_statut_promotion(request, promo_id):
    promo = get_object_or_404(Promotion, id=promo_id)
    promo.actif = not promo.actif
    promo.save()
    return redirect('liste_promotions')

@login_required
@user_passes_test(est_gestionnaire_stock)
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
@user_passes_test(est_gestionnaire_stock)
def detail_promotion(request, pk):
    promo = get_object_or_404(Promotion, pk=pk)
    produits = promo.produits.all()
    return render(request, 'appcedi/admin/detail_promotion.html', {'promo': promo, 'produits': produits})

@login_required
@user_passes_test(est_gestionnaire_stock)
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
@user_passes_test(est_gestionnaire_stock)
def supprimer_promotion(request, pk):
    promo = get_object_or_404(Promotion, pk=pk)
    if request.method == 'POST':
        titre = promo.titre
        promo.delete()
        messages.success(request, f'Promotion "{titre}" supprimée avec succès !')
        return redirect('liste_promotions')
    return render(request, 'appcedi/admin/supprimer_promotion.html', {'promo': promo})


# ========== CRUD COMMANDES (Gestionnaire de stock) ==========
@login_required
@user_passes_test(est_gestionnaire_stock)
def liste_commandes(request):
    query = request.GET.get('q', '').strip()
    commandes = Commande.objects.all().order_by('-date_commande')

    if query:
        commandes = commandes.filter(
            Q(reference_commande__icontains=query) | Q(client__username__icontains=query) | Q(client__email__icontains=query)
        )

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        html = render_to_string('appcedi/admin/partials/_commandes_rows.html', {'commandes': commandes})
        return JsonResponse({'html': html})

    return render(request, 'appcedi/admin/liste_commandes.html', {'commandes': commandes})

@login_required
@user_passes_test(est_gestionnaire_stock)
def detail_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    lignes = commande.lignes.all()
    return render(request, 'appcedi/admin/detail_commande.html', {'commande': commande, 'lignes': lignes})

@login_required
@user_passes_test(est_gestionnaire_stock)
def changer_statut_commande(request):
    if request.method == 'POST':
        commande_ids = request.POST.getlist('commande_ids')
        nouveau_statut = request.POST.get('statut')
        
        if not commande_ids or not nouveau_statut:
            return JsonResponse({'success': False, 'error': 'Données manquantes'}, status=400)

        commandes = Commande.objects.filter(id__in=commande_ids)
        commandes.update(statut=nouveau_statut)
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            query = request.POST.get('q', '').strip()
            commandes_list = Commande.objects.all().order_by('-date_commande')
            if query:
                commandes_list = commandes_list.filter(Q(reference_commande__icontains=query) | Q(client__username__icontains=query))
            html = render_to_string('appcedi/admin/partials/_commandes_rows.html', {'commandes': commandes_list})
            return JsonResponse({'success': True, 'html': html})
            
        return redirect('liste_commandes')
    return redirect('liste_commandes')


# ========== CRUD ARTICLES DE BLOG (Conseiller) ==========
@login_required
@user_passes_test(est_conseiller)
def liste_articles(request):
    query = request.GET.get('q', '').strip()
    articles = ArticleBlog.objects.all().order_by('-date_publication')

    if query:
        articles = articles.filter(Q(titre__icontains=query) | Q(auteur__username__icontains=query) | Q(categorie_article__icontains=query))

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        html = render_to_string('appcedi/admin/partials/_articles_rows.html', {'articles': articles})
        return JsonResponse({'html': html})

    return render(request, 'appcedi/admin/liste_articles.html', {'articles': articles})

@login_required
@user_passes_test(est_conseiller)
def actions_articles_bulk(request):
    if request.method == 'POST':
        article_ids = request.POST.getlist('article_ids')
        action = request.POST.get('action')
        if not article_ids:
            return JsonResponse({'success': False, 'error': 'Aucun article sélectionné.'})

        articles = ArticleBlog.objects.filter(id__in=article_ids)
        if action == 'delete': articles.delete()
        elif action == 'publier': articles.update(statut='publie')
        elif action == 'brouillon': articles.update(statut='brouillon')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            new_articles = ArticleBlog.objects.all().order_by('-date_publication')
            html = render_to_string('appcedi/admin/partials/_articles_rows.html', {'articles': new_articles})
            return JsonResponse({'success': True, 'html': html})

        return redirect('liste_articles')
    return redirect('liste_articles')

@login_required
@user_passes_test(est_conseiller)
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
@user_passes_test(est_conseiller)
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

@login_required
@user_passes_test(est_conseiller)
def supprimer_article(request, pk):
    article = get_object_or_404(ArticleBlog, pk=pk)
    if request.method == 'POST':
        titre = article.titre
        article.delete()
        messages.success(request, f'Article "{titre}" supprimé avec succès !')
        return redirect('liste_articles')
    return render(request, 'appcedi/admin/supprimer_article.html', {'article': article})

def article_detail(request, pk):
    article = get_object_or_404(ArticleBlog, pk=pk, statut='publie')
    articles_similaires = ArticleBlog.objects.filter(categorie_article=article.categorie_article, statut='publie').exclude(id=article.id)[:3]
    return render(request, 'appcedi/article_detail.html', {'article': article, 'articles_similaires': articles_similaires})


# ========== CRUD AVIS CLIENTS (Conseiller) ==========
@login_required
@user_passes_test(est_conseiller)
def liste_avis(request):
    query = request.GET.get('q', '').strip()
    avis_list = AvisClient.objects.all().order_by('-date_creation')

    if query:
        avis_list = avis_list.filter(Q(produit__titre__icontains=query) | Q(utilisateur__username__icontains=query))

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        html = render_to_string('appcedi/admin/partials/_avis_rows.html', {'avis': avis_list})
        return JsonResponse({'html': html})

    return render(request, 'appcedi/admin/liste_avis.html', {'avis': avis_list})

@login_required
@user_passes_test(est_conseiller)
def actions_avis_bulk(request):
    if request.method == 'POST':
        avis_ids = request.POST.getlist('avis_ids')
        action = request.POST.get('action')
        if not avis_ids:
            return JsonResponse({'success': False, 'error': 'Aucun avis sélectionné.'})

        qs = AvisClient.objects.filter(id__in=avis_ids)
        if action == 'approuve': qs.update(statut='approuve')
        elif action == 'rejete': qs.update(statut='rejete')
        elif action == 'en_attente': qs.update(statut='en_attente')
        elif action == 'delete': qs.delete()

        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string('appcedi/admin/partials/_avis_rows.html', {'avis': AvisClient.objects.all().order_by('-date_creation')})
            return JsonResponse({'success': True, 'html': html})

        return redirect('liste_avis')
    return redirect('liste_avis')

@login_required
@user_passes_test(est_conseiller)
def detail_avis(request, pk):
    avis = get_object_or_404(AvisClient, pk=pk)
    return render(request, 'appcedi/admin/detail_avis.html', {'avis': avis})

@login_required
@user_passes_test(est_conseiller)
def changer_statut_avis(request, pk):
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
@user_passes_test(est_conseiller)
def approuver_avis(request, pk):
    avis = get_object_or_404(AvisClient, pk=pk)
    avis.statut = 'approuve'
    avis.save()
    messages.success(request, 'Avis approuvé avec succès !')
    return redirect('liste_avis')

@login_required
@user_passes_test(est_conseiller)
def rejeter_avis(request, pk):
    avis = get_object_or_404(AvisClient, pk=pk)
    avis.statut = 'rejete'
    avis.save()
    messages.success(request, 'Avis rejeté.')
    return redirect('liste_avis')


# ========== TÉMOIGNAGES (Conseiller) ==========
@login_required
@user_passes_test(est_conseiller)
def liste_temoignages(request):
    query = request.GET.get('q', '').strip()
    temoignages = Temoignage.objects.all().order_by('-date_creation')

    if query:
        temoignages = temoignages.filter(Q(utilisateur__username__icontains=query) | Q(contenu__icontains=query))

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        html = render_to_string('appcedi/admin/partials/_temoignages_rows.html', {'temoignages': temoignages})
        return JsonResponse({'html': html})

    return render(request, 'appcedi/admin/liste_temoignages.html', {'temoignages': temoignages})

@login_required
@user_passes_test(est_conseiller)
def actions_temoignages_bulk(request):
    if request.method == 'POST':
        ids = request.POST.getlist('temoignage_ids')
        action = request.POST.get('action')
        if not ids:
            return JsonResponse({'success': False, 'error': 'Aucun témoignage sélectionné.'})

        qs = Temoignage.objects.filter(id__in=ids)
        if action == 'approuve': qs.update(statut='approuve')
        elif action == 'rejete': qs.update(statut='rejete')
        elif action == 'en_attente': qs.update(statut='en_attente')
        elif action == 'delete': qs.delete()

        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string('appcedi/admin/partials/_temoignages_rows.html', {'temoignages': Temoignage.objects.all().order_by('-date_creation')})
            return JsonResponse({'success': True, 'html': html})

        return redirect('liste_temoignages')
    return redirect('liste_temoignages')

@login_required
@user_passes_test(est_conseiller)
def detail_temoignage(request, pk):
    temoignage = get_object_or_404(Temoignage, pk=pk)
    return render(request, 'appcedi/admin/detail_temoignage.html', {'temoignage': temoignage})

@login_required
@user_passes_test(est_conseiller)
def approuver_temoignage(request, pk):
    temoignage = get_object_or_404(Temoignage, pk=pk)
    temoignage.statut = 'approuve'
    temoignage.save()
    messages.success(request, "Témoignage approuvé avec succès !")
    return redirect('liste_temoignages')

@login_required
@user_passes_test(est_conseiller)
def rejeter_temoignage(request, pk):
    temoignage = get_object_or_404(Temoignage, pk=pk)
    temoignage.statut = 'rejete'
    temoignage.save()
    messages.success(request, "Témoignage rejeté.")
    return redirect('liste_temoignages')

@login_required
@user_passes_test(est_conseiller)
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
@user_passes_test(est_conseiller)
def supprimer_temoignage(request, pk):
    temoignage = get_object_or_404(Temoignage, pk=pk)
    if request.method == 'POST':
        temoignage.delete()
        messages.success(request, "Témoignage supprimé.")
        return redirect('liste_temoignages')
    return render(request, 'appcedi/admin/supprimer_temoignage.html', {'temoignage': temoignage})

def liste_temoignages_publics(request):
    temoignages = Temoignage.objects.filter(statut='approuve').order_by('-date_creation')
    return render(request, 'appcedi/temoignages.html', {'temoignages': temoignages})

@login_required
def ajouter_temoignage_site(request):
    if request.method == 'POST':
        contenu = request.POST.get('commentaire') or request.POST.get('contenu')
        if contenu:
            Temoignage.objects.create(utilisateur=request.user, contenu=contenu, statut='en_attente')
            messages.success(request, "Merci ! Votre témoignage a été transmis à l'équipe.")
    return redirect(request.META.get('HTTP_REFERER', 'accueil'))

@login_required
def soumettre_temoignage(request):
    if request.method == 'POST':
        contenu = request.POST.get('contenu', '').strip()
        if contenu:
            Temoignage.objects.create(utilisateur=request.user, contenu=contenu, statut='en_attente')
            messages.success(request, "Merci ! Votre témoignage sera publié après modération.")
        else:
            messages.error(request, "Merci d'écrire votre témoignage avant d'envoyer.")
    return redirect(request.META.get('HTTP_REFERER', 'accueil'))


# ========== CRUD QUESTIONS CONSEILS (Conseiller) ==========
@login_required
@user_passes_test(est_conseiller)
def liste_questions(request):
    questions = QuestionConseil.objects.all().order_by('-date_question')
    return render(request, 'appcedi/admin/liste_questions.html', {'questions': questions})

@login_required
@user_passes_test(est_conseiller)
def repondre_question(request, pk):
    question = get_object_or_404(QuestionConseil, pk=pk)
    if request.method == 'POST':
        question.statut = 'repondu'
        question.save()
        messages.success(request, 'Question marquée comme répondue.')
        return redirect('liste_questions')
    return render(request, 'appcedi/admin/repondre_question.html', {'question': question})


# ========== PANIER & COMMANDES CLIENT ==========
def voir_panier(request):
    if request.user.is_authenticated:
        panier, created = Panier.objects.get_or_create(utilisateur=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        panier, created = Panier.objects.get_or_create(session_id=session_key)

    articles = panier.articles.all()
    # 👇 On utilise total_ligne() qui prend en compte le prix_unitaire (promo) 👇
    total = sum(article.total_ligne() for article in articles)
    
    context = {
        'panier': panier,
        'articles': articles,
        'total': total,
    }
    return render(request, 'appcedi/panier/panier_detail.html', context)


def ajouter_au_panier(request, produit_id):
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
    
    prix_envoye = request.POST.get('prix_promo')
    prix_final = int(prix_envoye) if prix_envoye else produit.prix

    # 👇 On cherche l'article par panier + produit + prix
    article, created = ArticlePanier.objects.get_or_create(
        panier=panier, 
        produit=produit,
        prix_unitaire=prix_final,  # ← La clé : on précise le prix
        defaults={'quantite': quantite}
    )
    
    if not created:
        # Si la ligne existait déjà à ce même prix, on ajoute juste la quantité
        article.quantite += quantite
        article.save()

    messages.success(request, f"{produit.titre} a été ajouté à votre panier.")
    return redirect('voir_panier')

def modifier_quantite_panier(request, article_id):
    article = get_object_or_404(ArticlePanier, id=article_id)
    action = request.POST.get('action')

    quantite_affichage = 0
    
    if action == 'augmenter':
        article.quantite += 1
        article.save()
        quantite_affichage = article.quantite
    elif action == 'reduire':
        if article.quantite > 1:
            article.quantite -= 1
            article.save()
            quantite_affichage = article.quantite
        else:
            article.delete()
            quantite_affichage = 0

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            panier = article.panier
            total = sum(item.total_ligne() for item in panier.articles.all())
        except:
            total = 0
            
        return JsonResponse({'success': True, 'quantite': quantite_affichage, 'total_panier': total})

    return redirect('voir_panier')


def supprimer_du_panier(request, article_id):
    article = get_object_or_404(ArticlePanier, id=article_id)
    article.delete()
    messages.info(request, "Article retiré du panier.")
    return redirect('voir_panier')


@login_required
def basculer_liste_souhaits(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id)
    souhait, created = ListeSouhaits.objects.get_or_create(utilisateur=request.user, produit=produit)
    
    if not created:
        souhait.delete()
        is_wishlisted = False
        message = "Retiré de vos souhaits."
    else:
        is_wishlisted = True
        message = "Ajouté à vos souhaits."

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_wishlisted': is_wishlisted, 'message': message})

    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'accueil'))


@login_required
def espace_client(request):
    tab = request.GET.get('tab', 'profil')
    form = None
    
    if request.method == 'POST' and request.POST.get('action') == 'update_profile':
        form = ModifierProfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre profil a été mis à jour avec succès !")
            return redirect(f"{request.path}?tab=profil")
    else:
        form = ModifierProfilForm(instance=request.user)

    commandes = Commande.objects.filter(client=request.user).order_by('-date_commande')
    souhaits = ListeSouhaits.objects.filter(utilisateur=request.user).select_related('produit')
    
    panier_items = []
    panier_total = 0
    try:
        panier = Panier.objects.get(utilisateur=request.user)
        panier_items = panier.articles.select_related('produit').all()
        panier_total = sum(item.produit.prix * item.quantite for item in panier_items)
    except Panier.DoesNotExist:
        pass

    context = {
        'active_tab': tab, 'form': form, 'commandes': commandes,
        'souhaits': souhaits, 'panier_items': panier_items, 'panier_total': panier_total,
    }
    return render(request, 'appcedi/espace_client.html', context)


@login_required
def ajouter_avis_produit(request, produit_id):
    if request.method == 'POST':
        produit = get_object_or_404(Produit, pk=produit_id)
        note = request.POST.get('note')
        commentaire = request.POST.get('commentaire', '')

        AvisClient.objects.update_or_create(
            produit=produit, utilisateur=request.user,
            defaults={'note': note, 'commentaire': commentaire, 'statut': 'en_attente'}
        )
        messages.success(request, "Merci ! Votre avis sera publié après modération.")
    return redirect('detail_produit', pk=produit_id)


@login_required
def valider_commande(request):
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
        mode_livraison = request.POST.get('mode_livraison', 'retrait')
        point_vente_id = request.POST.get('point_vente_retrait')
        adresse_livraison = request.POST.get('adresse_livraison', '')
        telephone = request.POST.get('telephone', '')
        
        # On utilise total_ligne() qui prend en compte le prix promotionnel
        total = sum(item.total_ligne() for item in articles)
        reference = f"CMD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        commande = Commande.objects.create(
            client=request.user, statut='attente_paiement', mode_livraison=mode_livraison,
            point_vente_retrait_id=point_vente_id if mode_livraison == 'retrait' else None,
            adresse_livraison=adresse_livraison if mode_livraison == 'livraison' else '',
            frais_port=0, montant_total=total, reference_commande=reference,
        )

        for item in articles:
            # On enregistre le prix réel (promo ou normal) dans la ligne de commande
            prix_final = item.prix_unitaire if item.prix_unitaire > 0 else item.produit.prix
            
            LigneCommande.objects.create(
                commande=commande, produit=item.produit,
                quantite=item.quantite, 
                prix_unitaire_au_moment=prix_final,
            )

        articles.delete()
        messages.success(request, f"Votre commande {reference} a été enregistrée avec succès !")
        return redirect('espace_client')

    # 👇 CALCUL DU TOTAL ET DU POIDS TOTAL 👇
    total = sum(item.total_ligne() for item in articles)
    
    poids_total = 0
    for item in articles:
        if item.produit.poids:
            poids_total += item.produit.poids * item.quantite

    return render(request, 'appcedi/panier/checkout.html', {
        'articles': articles, 
        'total': total, 
        'poids_total': poids_total, # 👈 Envoyé au template
        'points_vente': PointVente.objects.all()
    })


# ========== GESTION DES UTILISATEURS (Admin uniquement) ==========
# Formulaire pour MODIFIER un utilisateur (sans mot de passe)
class AdminUserUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Profil.ROLE_CHOICES, required=True, label="Rôle de l'utilisateur")

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pré-remplir le rôle actuel
        if self.instance and self.instance.pk:
            try:
                self.fields['role'].initial = self.instance.profil.role
            except Profil.DoesNotExist:
                pass

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profil, _ = Profil.objects.get_or_create(user=user)
            profil.role = self.cleaned_data['role']
            profil.save()
        return user

@login_required
@user_passes_test(est_admin)
def liste_utilisateurs(request):
    utilisateurs = User.objects.all().order_by('-date_joined')
    return render(request, 'appcedi/admin/liste_utilisateurs.html', {'utilisateurs': utilisateurs})

@login_required
@user_passes_test(est_admin)
def ajouter_utilisateur(request):
    if request.method == 'POST':
        form = AdminUserUpdateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilisateur créé avec succès.")
            return redirect('liste_utilisateurs')
    else:
        form = AdminUserUpdateForm()
    return render(request, 'appcedi/admin/form_utilisateur.html', {'form': form, 'titre': 'Ajouter un utilisateur'})

@login_required
@user_passes_test(est_admin)
def modifier_utilisateur(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    profil = user_obj.profil if hasattr(user_obj, 'profil') else None

    if request.method == 'POST':
        form = AdminUserUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilisateur modifié avec succès.")
            return redirect('liste_utilisateurs')
    else:
        initial = {'role': profil.role} if profil else {}
        form = AdminUserUpdateForm(instance=user_obj, initial=initial)
        
    return render(request, 'appcedi/admin/form_utilisateur.html', {'form': form, 'titre': 'Modifier un utilisateur'})

@login_required
@user_passes_test(est_admin)
def supprimer_utilisateur(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user_obj.delete()
        messages.success(request, "Utilisateur supprimé.")
        return redirect('liste_utilisateurs')
    return render(request, 'appcedi/admin/supprimer_utilisateur.html', {'user_obj': user_obj})

def page_contact(request):
    if request.method == 'POST':
        # 👇 On vérifie la connexion SEULEMENT ici, au moment de l'envoi
        if not request.user.is_authenticated:
            messages.warning(request, "Veuillez vous connecter pour envoyer un message.")
            return redirect(f"{request.path}?next={request.path}") # Redirige vers la page de connexion en gardant le retour
            
        nom = request.POST.get('nom')
        email = request.POST.get('email')
        sujet = request.POST.get('sujet')
        message = request.POST.get('message')
        
        messages.success(request, "Merci ! Votre message a bien été envoyé. Nous vous répondrons sous 48h.")
        return redirect('page_contact')
        
    return render(request, 'appcedi/contact.html')