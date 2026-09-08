from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum
from .models import *
from .forms import *

# ========== VÉRIFICATION DES DROITS ==========
def est_admin_ou_gestionnaire(user):
    return user.is_superuser or (hasattr(user, 'role') and user.role in ['admin', 'gestionnaire_stock'])

# ========== PAGE D'ACCUEIL ==========
from django.utils import timezone
from datetime import datetime

# ========== PAGE D'ACCUEIL ==========
def accueil(request):
    now = timezone.now()
    
    # Récupère toutes les promotions valides dans la plage de dates
    promotions_actives = Promotion.objects.filter(
        date_debut__lte=now,
        date_fin__gte=now
    ).prefetch_related('produits')

    promos_data = []
    for promo in promotions_actives:
        produits_promo = []
        for produit in promo.produits.filter(statut=True):
            # Utilisation de la méthode du modèle si elle existe, sinon calcul direct
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

    # Debug dans la console du terminal
    print(f"--- DEBUG ACCUEIL ---")
    print(f"Heure actuelle (now): {now}")
    print(f"Promotions trouvées en BD: {promotions_actives.count()}")
    print(f"Promotions envoyées au template: {len(promos_data)}")

    context = {
        'points_de_vente': PointVente.objects.all(),
        'produits_recents': Produit.objects.filter(statut=True).order_by('-id')[:8],
        'promos_data': promos_data,
        'articles_blog': ArticleBlog.objects.filter(statut='publie').order_by('-date_publication')[:3],
    }
    
    return render(request, 'appcedi/accueil.html', context)

# ========== AUTHENTIFICATION ==========
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

def inscription(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Bienvenue {user.username} !')
            return redirect('accueil')
    else:
        form = UserCreationForm()
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

# ========== TABLEAU DE BORD ==========
@login_required
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
    }
    return render(request, 'appcedi/tableau_de_bord.html', context)

# ========== CRUD PRODUITS ==========
@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def liste_produits(request):
    produits = Produit.objects.all().order_by('-id')
    return render(request, 'appcedi/admin/liste_produits.html', {'produits': produits})

# views.py

# views.py

@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def ajouter_produit(request):
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            produit = form.save()
            
            # Récupération de l'ensemble des fichiers transmis dynamiquement
            fichiers = request.FILES.getlist('images_multiples')
            for index, f in enumerate(fichiers):
                if f:
                    Image.objects.create(
                        produit=produit,
                        url_image=f,
                        est_principale=(index == 0) # La 1ère image devient l'image principale
                    )
            
            messages.success(request, f'Produit "{produit.titre}" ajouté avec succès !')
            return redirect('liste_produits')
    else:
        form = ProduitForm()
    return render(request, 'appcedi/admin/ajouter_produit.html', {'form': form})

def detail_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk, statut=True)
    images = produit.images.all()
    image_principale = images.filter(est_principale=True).first()
    if not image_principale and images.exists():
        image_principale = images.first()
    autres_images = images.exclude(pk=image_principale.pk) if image_principale else images

    avis_approuves = produit.avis.filter(statut='approuve')
    note_moyenne = produit.moyenne_avis()
    total_avis = avis_approuves.count()

    # Pour la répartition des notes (barres)
    repartition = {}
    for i in range(1, 6):
        repartition[i] = avis_approuves.filter(note=i).count()

    # Produits similaires (même catégorie, exclure le produit courant)
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
        'points_vente': PointVente.objects.all(),  # pour la disponibilité
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
            
            # Récupération des nouvelles images ajoutées
            fichiers = request.FILES.getlist('images_multiples')
            for f in fichiers:
                if f:
                    Image.objects.create(
                        produit=produit,
                        url_image=f,
                        est_principale=False
                    )
            
            # Si aucune image principale n'est définie, définir la toute première image disponible
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
# appcedi/views.py
@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def definir_principale(request, image_id):
    image = get_object_or_404(Image, pk=image_id)
    produit = image.produit
    # Désactiver toutes les autres images du même produit
    produit.images.update(est_principale=False)
    # Activer celle-ci
    image.est_principale = True
    image.save()
    messages.success(request, "Image définie comme principale.")
    return redirect('modifier_produit', pk=produit.pk)

@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def supprimer_image(request, image_id):
    image = get_object_or_404(Image, pk=image_id)
    produit = image.produit
    # Si c'était l'image principale, on en remet une autre (la première restante)
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
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Promotion

def liste_promotions(request):
    maintenant = timezone.now()
    # On récupère toutes les promotions sans restriction
    promotions = Promotion.objects.all().order_by('-date_debut')
    
    # On ajoute des informations dynamiques sur le statut pour le template
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

# Vue pour activer/désactiver directement depuis la liste
def basculer_statut_promotion(request, promo_id):
    promo = get_object_or_404(Promotion, id=promo_id)
    promo.actif = not promo.actif  # Inverse le statut (True -> False / False -> True)
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
    # Récupérer 3 articles similaires (même catégorie, sauf lui-même)
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
def approuver_avis(request, pk):
    avis = get_object_or_404(AvisClient, pk=pk)
    avis.statut = 'approuve'
    avis.save()
    messages.success(request, f'Avis approuvé avec succès !')
    return redirect('liste_avis')

@login_required
@user_passes_test(est_admin_ou_gestionnaire)
def rejeter_avis(request, pk):
    avis = get_object_or_404(AvisClient, pk=pk)
    avis.statut = 'rejete'
    avis.save()
    messages.success(request, f'Avis rejeté.')
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
        # Ici tu peux ajouter un système de réponse
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

from django.db.models import Count, Avg
from .models import PointVente, Produit, AvisClient

def a_propos(request):
    # Récupération des points de vente
    points_vente = PointVente.objects.all()
    
    # Chiffres clés dynamiques
    nb_librairies = points_vente.count()
    nb_produits = Produit.objects.filter(statut=True).count()
    nb_avis = AvisClient.objects.filter(statut='approuve').count()
    
    context = {
        'points_vente': points_vente,
        'nb_librairies': nb_librairies,
        'nb_produits': nb_produits,
        'nb_avis': nb_avis,
    }
    return render(request, 'appcedi/a_propos.html', context)