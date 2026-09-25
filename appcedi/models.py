from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from django.conf import settings

class Categorie(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    categorie_parente = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True)
    def __str__(self):
        return self.nom

class PointVente(models.Model):
    nom = models.CharField(max_length=100)
    adresse_complete = models.TextField()
    telephone = models.CharField(max_length=20, blank=True, null=True)
    horaires_ouverture = models.CharField(max_length=255, blank=True, null=True)
    url_image = models.ImageField(upload_to='points_vente/', blank=True, null=True)
    def __str__(self):
        return self.nom

class Produit(models.Model):
    TYPES = (('livre', 'Livre'), ('bible', 'Bible'), ('cd', 'CD'), ('cadeau', 'Cadeau'))
    titre = models.CharField(max_length=255)
    auteur = models.CharField(max_length=255, blank=True, null=True)
    editeur = models.CharField(max_length=255, blank=True, null=True)
    isbn = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField()
    prix = models.IntegerField()
    poids = models.FloatField(blank=True, null=True)
    type_produit = models.CharField(max_length=20, choices=TYPES, default='livre')
    est_edition_cedi = models.BooleanField(default=False)
    quantite_stock = models.IntegerField(default=0)
    seuil_alerte = models.IntegerField(default=3)
    statut = models.BooleanField(default=True)
    categories = models.ManyToManyField(Categorie, through='ProduitCategorie', blank=True)

    def moyenne_avis(self):
        avis = self.avis.filter(statut='approuve')
        if avis.exists():
            return round(sum(a.note for a in avis) / avis.count(), 1)
        return 0

    def nombre_avis(self):
        return self.avis.filter(statut='approuve').count()

    # 👇 Cette méthode doit être À L'INTÉRIEUR de la classe
    def image_principale(self):
        """Retourne l'image principale du produit, ou la première si aucune n'est définie."""
        img = self.images.filter(est_principale=True).first()
        if not img:
            img = self.images.first()
        return img

    def __str__(self):
        return self.titre

class ProduitCategorie(models.Model):
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE)

class Image(models.Model):
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name='images')
    url_image = models.ImageField(upload_to='produits/')
    est_principale = models.BooleanField(default=False)
    def __str__(self):
        return f"Image de {self.produit.titre}"

class Promotion(models.Model):
    TYPE_REDUCTIONS = [
        ('pourcentage', 'Pourcentage'),
        ('fixe', 'Montant fixe'),
    ]

    titre = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    type_reduction = models.CharField(max_length=20, choices=TYPE_REDUCTIONS)
    valeur_reduction = models.FloatField()
    date_debut = models.DateTimeField(blank=True, null=True)
    date_fin = models.DateTimeField(blank=True, null=True)
    code_promo = models.CharField(max_length=50, blank=True, null=True)
    est_vente_flash = models.BooleanField(default=False)
    actif = models.BooleanField(default=True)
    produits = models.ManyToManyField('Produit', through='ProduitPromotion')

    def __str__(self):
        return self.titre

    @property
    def est_en_cours(self):
        """Vérifie si la promotion est active et dans le créneau horaire exact."""
        now = timezone.now()
        return self.actif and (self.date_debut <= now <= self.date_fin)

    def calculer_prix_reduit(self, prix_original):
        """Calcule le prix réduit pour un produit donné."""
        if self.type_reduction == 'pourcentage':
            prix = prix_original * (1 - self.valeur_reduction / 100)
        else:  # montant fixe
            prix = prix_original - self.valeur_reduction
        return max(0, round(prix))  # Évite les prix négatifs

class ProduitPromotion(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    

    
from django.db import models
from django.conf import settings

# 1. Avis/Témoignage général sur le site
# appcedi/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AvisClient(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('approuve', 'Approuvé'),
        ('rejete', 'Rejeté'),
    ]

    produit = models.ForeignKey('Produit', on_delete=models.CASCADE, related_name='avis')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.PositiveSmallIntegerField(default=5)  # 1 à 5
    commentaire = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='approuve')
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Avis de {self.utilisateur} sur {self.produit}"


# 2. Avis spécifique sur un produit avec une note
class AvisProduit(models.Model):
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE, related_name='avis_produits')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avis_produits')
    note = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)], default=5)
    commentaire = models.TextField(verbose_name="Avis produit")
    approuve = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Avis Produit"
        verbose_name_plural = "Avis Produits"
        ordering = ['-date_creation']

    def __str__(self):
        return f"Avis de {self.utilisateur.username} sur {self.produit.nom} ({self.note}/5)"    

class Commande(models.Model):
    STATUTS = (('attente_paiement', 'En attente de paiement'), ('payee', 'Payée'), ('en_preparation', 'En préparation'), ('prete_retrait', 'Prête pour retrait'), ('expediee', 'Expédiée'), ('livree', 'Livrée'))
    MODES = (('retrait', 'Retrait en point de vente'), ('livraison', 'Livraison à domicile'))
    client = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_commande = models.DateTimeField(default=timezone.now)
    statut = models.CharField(max_length=20, choices=STATUTS, default='attente_paiement')
    mode_livraison = models.CharField(max_length=20, choices=MODES)
    point_vente_retrait = models.ForeignKey(PointVente, on_delete=models.SET_NULL, null=True, blank=True)
    adresse_livraison = models.TextField(blank=True, null=True)
    frais_port = models.IntegerField(default=0)
    montant_total = models.IntegerField()
    reference_commande = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return f"Commande {self.reference_commande}"

class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='lignes')
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.IntegerField()
    prix_unitaire_au_moment = models.IntegerField()


class ArticleBlog(models.Model):
    CATEGORIES = (('enseignement', 'Enseignement BM'), ('verite_fondamentale', 'Vérité fondamentale'), ('conseil', 'Conseil spirituel'), ('partage', 'Partage de lecture'))
    titre = models.CharField(max_length=255)
    contenu = models.TextField()
    auteur = models.ForeignKey(User, on_delete=models.CASCADE)
    date_publication = models.DateTimeField(default=timezone.now)
    categorie_article = models.CharField(max_length=30, choices=CATEGORIES)
    statut = models.CharField(max_length=20, choices=[('brouillon', 'Brouillon'), ('publie', 'Publié')], default='brouillon')
    def __str__(self):
        return self.titre
    
# ================= PANIER =================
class Panier(models.Model):
    utilisateur = models.OneToOneField(User, on_delete=models.CASCADE, related_name='panier', null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def total_panier(self):
        return sum(item.total_ligne() for item in self.articles.all())

class ArticlePanier(models.Model):
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE, related_name='articles')
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)

    def total_ligne(self):
        return self.produit.prix * self.quantite

# ================= LISTE DE SOUHAITS =================
class ListeSouhaits(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='souhaits')
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('utilisateur', 'produit')    

class QuestionConseil(models.Model):
    auteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    titre_question = models.CharField(max_length=255)
    message = models.TextField()
    date_question = models.DateTimeField(default=timezone.now)
    statut = models.CharField(max_length=20, choices=[('en_attente', 'En attente'), ('repondu', 'Répondu')], default='en_attente')
    
    
class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    telephone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Profil de {self.user.username}"
    
class Temoignage(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('approuve', 'Approuvé'),
        ('rejete', 'Rejeté'),
    ]

    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='temoignages')
    contenu = models.TextField(verbose_name="Témoignage")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Témoignage"
        verbose_name_plural = "Témoignages"
        ordering = ['-date_creation']

    def __str__(self):
        return f"Témoignage de {self.utilisateur.username}"
    
