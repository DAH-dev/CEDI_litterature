from django import forms
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import *


# ========== FORMULAIRE PRODUIT ==========
class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = [
            'titre', 'auteur', 'editeur', 'isbn', 'description', 'prix', 
            'poids', 'type_produit', 'est_edition_cedi', 'quantite_stock', 
            'seuil_alerte', 'statut', 'categories'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'categories': forms.SelectMultiple(attrs={'class': 'w-full border rounded px-3 py-2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 👇 RENDRE LE CHAMP CATÉGORIES OPTIONNEL
        self.fields['categories'].required = False

        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-cediRed'
                })


# ========== AUTRES FORMULAIRES ==========
class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ['nom', 'description', 'categorie_parente']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if not isinstance(self.fields[field].widget, forms.CheckboxInput):
                self.fields[field].widget.attrs.update({
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-cediRed'
                })


class PointVenteForm(forms.ModelForm):
    class Meta:
        model = PointVente
        fields = ['nom', 'adresse_complete', 'telephone', 'horaires_ouverture', 'url_image']
        widgets = {'adresse_complete': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if not isinstance(self.fields[field].widget, forms.CheckboxInput):
                self.fields[field].widget.attrs.update({
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-cediRed'
                })


# ========== FORMULAIRE PROMOTION ==========
class PromotionForm(forms.ModelForm):
    duree_heures = forms.FloatField(
        required=False,
        label="Durée rapide (en heures)",
        help_text="Exemple : 2.5 pour 2h30 min. Le système calculera la fin à partir de maintenant.",
        widget=forms.NumberInput(attrs={'placeholder': 'Ex: 2.5', 'step': '0.5'})
    )

    class Meta:
        model = Promotion
        fields = [
            'titre', 'description', 'type_reduction', 'valeur_reduction', 
            'duree_heures', 'date_debut', 'date_fin', 'code_promo', 
            'est_vente_flash', 'actif', 'produits'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'date_debut': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'date_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'produits': forms.SelectMultiple(attrs={'class': 'w-full border rounded px-3 py-2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre les dates non obligatoires côté HTML pour autoriser le mode Durée
        self.fields['date_debut'].required = False
        self.fields['date_fin'].required = False

        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-cediRed'
                })

    def clean(self):
        cleaned_data = super().clean()
        duree = cleaned_data.get('duree_heures')
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')

        # Si une durée est indiquée (Vente Flash rapide)
        if duree:
            now = timezone.now()
            cleaned_data['date_debut'] = now
            cleaned_data['date_fin'] = now + timedelta(hours=duree)
            cleaned_data['est_vente_flash'] = True

        # Si des dates manuelles sont saisies
        elif date_debut and date_fin:
            if date_fin <= date_debut:
                raise forms.ValidationError("La date de fin doit être postérieure à la date de début.")
        else:
            raise forms.ValidationError(
                "Remplis soit la durée en heures (pour une vente rapide), soit la plage de dates."
            )

        return cleaned_data


# ========== FORMULAIRE ARTICLE BLOG ==========
class ArticleBlogForm(forms.ModelForm):
    class Meta:
        model = ArticleBlog
        fields = ['titre', 'contenu', 'categorie_article', 'statut']
        widgets = {'contenu': forms.Textarea(attrs={'rows': 8})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if not isinstance(self.fields[field].widget, forms.CheckboxInput):
                self.fields[field].widget.attrs.update({
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-cediRed'
                })


# ========== FORMULAIRE IMAGE ==========
class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ['produit', 'url_image', 'est_principale']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if not isinstance(self.fields[field].widget, forms.CheckboxInput):
                self.fields[field].widget.attrs.update({
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-cediRed'
                })


# ========== FORMULAIRE INSCRIPTION ==========

class InscriptionForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Adresse email")
    telephone = forms.CharField(
        max_length=20, 
        required=True, 
        label="Numéro de téléphone",
        widget=forms.TextInput(attrs={'placeholder': '+225 07 00 00 00 00'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'telephone', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Nom d'utilisateur"
        self.fields['password1'].label = "Mot de passe"
        self.fields['password2'].label = "Confirmer le mot de passe"

        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-cediRed'
            })

    def save(self, commit=True):
        user = super().save(commit=commit)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Création du profil associé avec le téléphone
            Profil.objects.create(
                user=user,
                telephone=self.cleaned_data.get('telephone')
            )
        return user


# ========== FORMULAIRE CONNEXION ==========
class ConnexionForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Nom d'utilisateur"
        self.fields['password'].label = "Mot de passe"

        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-cediRed'
            })