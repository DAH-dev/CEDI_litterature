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

from django.contrib import admin
from .models import AvisClient


@admin.register(AvisClient)
class AvisClientAdmin(admin.ModelAdmin):
    list_display = ('produit', 'utilisateur', 'note', 'statut', 'date_creation')
    list_filter = ('statut', 'note', 'date_creation')
    search_fields = ('produit__titre', 'utilisateur__username', 'commentaire')
    list_editable = ('statut',)  # Modifier le statut directement dans la liste
    actions = ['approuver_avis', 'rejeter_avis', 'remettre_en_attente']

    def approuver_avis(self, request, queryset):
        count = queryset.update(statut='approuve')
        self.message_user(request, f"✅ {count} avis approuvé(s).")
    approuver_avis.short_description = "✅ Approuver les avis sélectionnés"

    def rejeter_avis(self, request, queryset):
        count = queryset.update(statut='rejete')
        self.message_user(request, f"❌ {count} avis rejeté(s).")
    rejeter_avis.short_description = "❌ Rejeter les avis sélectionnés"

    def remettre_en_attente(self, request, queryset):
        count = queryset.update(statut='en_attente')
        self.message_user(request, f"⏳ {count} avis remis en attente.")
    remettre_en_attente.short_description = "⏳ Remettre en attente"
    
from .models import Temoignage


@admin.register(Temoignage)
class TemoignageAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'extrait', 'statut', 'date_creation')
    list_filter = ('statut', 'date_creation')
    search_fields = ('utilisateur__username', 'contenu')
    list_editable = ('statut',)
    actions = ['approuver_temoignages', 'rejeter_temoignages', 'remettre_en_attente']

    def extrait(self, obj):
        return obj.contenu[:60] + ('...' if len(obj.contenu) > 60 else '')
    extrait.short_description = "Contenu"

    def approuver_temoignages(self, request, queryset):
        count = queryset.update(statut='approuve')
        self.message_user(request, f"✅ {count} témoignage(s) approuvé(s).")
    approuver_temoignages.short_description = "✅ Approuver les témoignages"

    def rejeter_temoignages(self, request, queryset):
        count = queryset.update(statut='rejete')
        self.message_user(request, f"❌ {count} témoignage(s) rejeté(s).")
    rejeter_temoignages.short_description = "❌ Rejeter les témoignages"

    def remettre_en_attente(self, request, queryset):
        count = queryset.update(statut='en_attente')
        self.message_user(request, f"⏳ {count} témoignage(s) remis en attente.")
    remettre_en_attente.short_description = "⏳ Remettre en attente"
    
    
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