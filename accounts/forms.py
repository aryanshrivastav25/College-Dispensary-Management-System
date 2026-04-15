
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from accounts.models import UserProfile

User = get_user_model()


class RegistrationForm(UserCreationForm):
    """Register a new CampusCare user and capture profile details."""

    role = forms.ChoiceField(
        choices=[
            (UserProfile.Role.DOCTOR, 'Doctor'),
            (UserProfile.Role.PHARMACIST, 'Pharmacist'),
        ]
    )
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'role',
            'phone',
            'password1',
            'password2',
        )

    def clean_email(self) -> str:
        """Reject duplicate email addresses."""
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self) -> dict:
        """Enforce student-only academic fields."""
        cleaned_data = super().clean()
        selected_role = cleaned_data.get('role')

        return cleaned_data

    def save(self, commit: bool = True):
        """Persist the user and synchronize the related profile."""
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            profile = user.profile
            profile.role = self.cleaned_data['role']
            profile.phone = self.cleaned_data['phone'].strip()
            profile.save()

        return user


class ProfileForm(forms.ModelForm):
    """Update the campus-specific fields attached to a user profile."""

    class Meta:
        model = UserProfile
        fields = ('roll_number', 'phone', 'year_of_study')

    def clean_roll_number(self) -> str:
        """Normalize roll numbers for consistent storage."""
        roll_number = self.cleaned_data.get('roll_number', '').strip().upper()
        queryset = UserProfile.objects.filter(roll_number=roll_number)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if roll_number and queryset.exists():
            raise forms.ValidationError('This roll number is already linked to another account.')
        return roll_number
    

class StudentRegistrationForm(UserCreationForm):
    """Register a new CampusCare user and capture profile details."""

    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    roll_number = forms.CharField(max_length=30, required=False)
    phone = forms.CharField(max_length=20, required=False)
    year_of_study = forms.IntegerField(min_value=1, max_value=8, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'roll_number',
            'phone',
            'year_of_study',
            'password1',
            'password2',
        )

    def clean_email(self) -> str:
        """Reject duplicate email addresses."""
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_roll_number(self) -> str:
        """Normalize roll numbers for consistent storage."""
        roll_number = self.cleaned_data.get('roll_number', '').strip().upper()
        if roll_number and UserProfile.objects.filter(roll_number=roll_number).exists():
            raise forms.ValidationError('This roll number is already linked to another account.')
        return roll_number

    def clean(self) -> dict:
        """Enforce student-only academic fields."""
        cleaned_data = super().clean()

        if not cleaned_data.get('roll_number'):
            self.add_error('roll_number', 'Roll number is required for students.')
        if not cleaned_data.get('year_of_study'):
            self.add_error('year_of_study', 'Year of study is required for students.')
        
        return cleaned_data

    def save(self, commit: bool = True):
        """Persist the user and synchronize the related profile."""
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            profile = user.profile
            profile.role = UserProfile.Role.STUDENT
            profile.roll_number = self.cleaned_data['roll_number'] or None
            profile.phone = self.cleaned_data['phone'].strip()
            profile.year_of_study = self.cleaned_data['year_of_study']
            profile.save()

        return user
    