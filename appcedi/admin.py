from django.contrib import admin
from .models import *

class ProduitAdmin(admin.ModelAdmin):
    list_display = ('titre', 'auteur', 'prix', 'quantite_stock', 'est_edition_cedi', 'statut')
    list_filter = ('est_edition_cedi', 'statut', 'type_produit')
    search_fields = ('titre', 'auteur', 'editeur', 'isbn')
    list_editable = ('prix', 'quantite_stock', 'statut')

class PointVenteAdmin(admin.ModelAdmin):
    list_display = ('nom', 'adresse_complete', 'telephone')
    search_fields = ('nom', 'adresse_complete')

class PromotionAdmin(admin.ModelAdmin):
    list_display = ('titre', 'type_reduction', 'valeur_reduction', 'date_debut', 'date_fin', 'est_vente_flash')
    list_filter = ('est_vente_flash',)
    search_fields = ('titre',)

class ArticleBlogAdmin(admin.ModelAdmin):
    list_display = ('titre', 'auteur', 'categorie_article', 'date_publication', 'statut')
    list_filter = ('categorie_article', 'statut')
    search_fields = ('titre', 'contenu')

@admin.register(AvisClient)
class AvisClientAdmin(admin.ModelAdmin):
    list_display = ('produit', 'utilisateur', 'note', 'date_creation', 'statut')
    list_filter = ('statut', 'note', 'date_creation')
    search_fields = ('produit__titre', 'utilisateur__username', 'commentaire')
    list_editable = ('statut',)

# Enregistrement des autres modèles
admin.site.register(Produit, ProduitAdmin)
admin.site.register(PointVente, PointVenteAdmin)
admin.site.register(Promotion, PromotionAdmin)
admin.site.register(ArticleBlog, ArticleBlogAdmin)
# La ligne AvisClient a été supprimée d'ici pour éviter le doublon
admin.site.register(Categorie)
admin.site.register(Image)
admin.site.register(Commande)
admin.site.register(LigneCommande)
admin.site.register(QuestionConseil)
admin.site.register(ProduitCategorie)
admin.site.register(ProduitPromotion)