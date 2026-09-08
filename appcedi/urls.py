from django.urls import path
from . import views

urlpatterns = [
    # Accueil
    path('', views.accueil, name='accueil'),
    
    # Authentification
    path('inscription/', views.inscription, name='inscription'),
    path('connexion/', views.connexion, name='connexion'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),
    
    # Tableau de bord
    path('tableau-de-bord/', views.tableau_de_bord, name='tableau_de_bord'),
    
    # Produits
    path('admin_produits/', views.liste_produits, name='liste_produits'),
    path('admin_produits/ajouter/', views.ajouter_produit, name='ajouter_produit'),
    # Détail d'un produit
    path('produit/<int:pk>/', views.detail_produit, name='detail_produit'),
    path('admin_produits/modifier/<int:pk>/', views.modifier_produit, name='modifier_produit'),
    path('admin_produits/supprimer/<int:pk>/', views.supprimer_produit, name='supprimer_produit'),
    path('produits/<int:pk>/basculer-statut/', views.basculer_statut_produit, name='basculer_statut_produit'),
    path('gestion_images/principale/<int:image_id>/', views.definir_principale, name='definir_principale'),
    path('gestion_images/supprimer/<int:image_id>/', views.supprimer_image, name='supprimer_image'),
    # Catégories
    path('admin_categories/', views.liste_categories, name='liste_categories'),
    path('admin_categories/ajouter/', views.ajouter_categorie, name='ajouter_categorie'),
    path('admin_categories/modifier/<int:pk>/', views.modifier_categorie, name='modifier_categorie'),
    path('admin_categories/supprimer/<int:pk>/', views.supprimer_categorie, name='supprimer_categorie'),
    
    # Points de vente
    path('admin_points_vente/', views.liste_points_vente, name='liste_points_vente'),
    path('admin_points_vente/ajouter/', views.ajouter_point_vente, name='ajouter_point_vente'),
    path('admin_points_vente/modifier/<int:pk>/', views.modifier_point_vente, name='modifier_point_vente'),
    path('admin_points_vente/supprimer/<int:pk>/', views.supprimer_point_vente, name='supprimer_point_vente'),
    
    path('admin_promotions/', views.liste_promotions, name='liste_promotions'),
    path('admin_promotions/ajouter/', views.ajouter_promotion, name='ajouter_promotion'),
    path('promotions/toggle/<int:promo_id>/', views.basculer_statut_promotion, name='basculer_statut_promotion'),
    path('admin_promotions/modifier/<int:pk>/', views.modifier_promotion, name='modifier_promotion'),
    path('admin_promotions/supprimer/<int:pk>/', views.supprimer_promotion, name='supprimer_promotion'),

    path('admin_articles/', views.liste_articles, name='liste_articles'),
    path('admin_articles/ajouter/', views.ajouter_article, name='ajouter_article'),
    path('articles/<int:pk>/', views.article_detail, name='article_detail'),
    path('admin_articles/modifier/<int:pk>/', views.modifier_article, name='modifier_article'),
    path('admin_articles/supprimer/<int:pk>/', views.supprimer_article, name='supprimer_article'),
    
    # Avis clients
    path('admin_avis/', views.liste_avis, name='liste_avis'),
    path('admin_avis/approuver/<int:pk>/', views.approuver_avis, name='approuver_avis'),
    path('admin_avis/rejeter/<int:pk>/', views.rejeter_avis, name='rejeter_avis'),
    
    # Questions conseils
    path('admin_questions/', views.liste_questions, name='liste_questions'),
    path('admin_questions/repondre/<int:pk>/', views.repondre_question, name='repondre_question'),
    
    # Commandes
    path('admin_commandes/', views.liste_commandes, name='liste_commandes'),
    path('admin_commandes/statut/<int:pk>/', views.changer_statut_commande, name='changer_statut_commande'),
    path('a-propos/', views.a_propos, name='a_propos'),
]