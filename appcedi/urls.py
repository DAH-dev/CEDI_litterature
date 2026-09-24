from django.urls import path
from . import views

urlpatterns = [
    # --- ACCUEIL & COMPTE ---
    path('', views.accueil, name='accueil'),
    path('inscription/', views.inscription, name='inscription'),
    path('connexion/', views.connexion, name='connexion'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),
    path('a-propos/', views.a_propos, name='a_propos'),

    # --- TABLEAU DE BORD ADMIN ---
    path('tableau-de-bord/', views.tableau_de_bord, name='tableau_de_bord'),

    # --- PRODUITS (BOUTIQUE & ADMIN) ---
    path('produit/<int:pk>/', views.detail_produit, name='detail_produit'),
    path('produit/<int:produit_id>/avis/ajouter/', views.ajouter_avis_produit, name='ajouter_avis_produit'),
    
    path('admin_produits/', views.liste_produits, name='liste_produits'),
    path('admin_produits/ajouter/', views.ajouter_produit, name='ajouter_produit'),
    path('admin_produits/modifier/<int:pk>/', views.modifier_produit, name='modifier_produit'),
    path('admin_produits/supprimer/<int:pk>/', views.supprimer_produit, name='supprimer_produit'),
    path('produits/<int:pk>/basculer-statut/', views.basculer_statut_produit, name='basculer_statut_produit'),
    path('gestion_images/principale/<int:image_id>/', views.definir_principale, name='definir_principale'),
    path('gestion_images/supprimer/<int:image_id>/', views.supprimer_image, name='supprimer_image'),

    # --- PANIER & LISTE DE SOUHAITS ---
    path('panier/', views.voir_panier, name='voir_panier'),
    path('panier/ajouter/<int:produit_id>/', views.ajouter_au_panier, name='ajouter_au_panier'),
    path('panier/modifier/<int:article_id>/', views.modifier_quantite_panier, name='modifier_quantite_panier'),
    path('panier/supprimer/<int:article_id>/', views.supprimer_du_panier, name='supprimer_du_panier'),
    path('panier/valider/', views.valider_commande, name='valider_commande'),
    path('produit/<int:pk>/ajouter-avis/', views.ajouter_avis_produit, name='ajouter_avis_produit'),

    path('liste-souhaits/', views.voir_liste_souhaits, name='voir_liste_souhaits'),
    path('liste-souhaits/basculer/<int:produit_id>/', views.basculer_liste_souhaits, name='basculer_liste_souhaits'),
    # Espace client centralisé
    path('espace-client/', views.espace_client, name='espace_client'),


    # --- CATEGORIES ---
    path('admin_categories/', views.liste_categories, name='liste_categories'),
    path('admin_categories/ajouter/', views.ajouter_categorie, name='ajouter_categorie'),
    path('admin_categories/modifier/<int:pk>/', views.modifier_categorie, name='modifier_categorie'),
    path('admin_categories/supprimer/<int:pk>/', views.supprimer_categorie, name='supprimer_categorie'),

    # --- POINTS DE VENTE ---
    path('admin_points_vente/', views.liste_points_vente, name='liste_points_vente'),
    path('admin_points_vente/ajouter/', views.ajouter_point_vente, name='ajouter_point_vente'),
    path('admin_points_vente/modifier/<int:pk>/', views.modifier_point_vente, name='modifier_point_vente'),
    path('admin_points_vente/supprimer/<int:pk>/', views.supprimer_point_vente, name='supprimer_point_vente'),

    # --- PROMOTIONS ---
    path('admin_promotions/', views.liste_promotions, name='liste_promotions'),
    path('admin_promotions/ajouter/', views.ajouter_promotion, name='ajouter_promotion'),
    path('promotions/toggle/<int:promo_id>/', views.basculer_statut_promotion, name='basculer_statut_promotion'),
    path('admin_promotions/modifier/<int:pk>/', views.modifier_promotion, name='modifier_promotion'),
    path('admin_promotions/supprimer/<int:pk>/', views.supprimer_promotion, name='supprimer_promotion'),

    # --- BLOG / ARTICLES ---
    path('admin_articles/', views.liste_articles, name='liste_articles'),
    path('admin_articles/ajouter/', views.ajouter_article, name='ajouter_article'),
    path('articles/<int:pk>/', views.article_detail, name='article_detail'),
    path('admin_articles/modifier/<int:pk>/', views.modifier_article, name='modifier_article'),
    path('admin_articles/supprimer/<int:pk>/', views.supprimer_article, name='supprimer_article'),

    # --- MODERATION AVIS ---
    path('admin_avis/', views.liste_avis, name='liste_avis'),
    path('admin_avis/approuver/<int:pk>/', views.approuver_avis, name='approuver_avis'),
    path('admin_avis/rejeter/<int:pk>/', views.rejeter_avis, name='rejeter_avis'),

    # --- QUESTIONS / CONSEILS ---
    path('admin_questions/', views.liste_questions, name='liste_questions'),
    path('admin_questions/repondre/<int:pk>/', views.repondre_question, name='repondre_question'),

    # --- COMMANDES (ADMIN) ---
    path('admin_commandes/', views.liste_commandes, name='liste_commandes'),
    path('admin_commandes/statut/<int:pk>/', views.changer_statut_commande, name='changer_statut_commande'),
    path('temoignage/ajouter/', views.ajouter_temoignage_site, name='ajouter_temoignage_site'),
    
    path('catalogue/', views.liste_catalogue, name='liste_catalogue'),
    path('ressources/', views.liste_ressources, name='liste_ressources'),
]