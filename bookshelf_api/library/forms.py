from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(rating, f"{rating}/5") for rating in range(1, 6)],
        coerce=int,
        label="Rating",
    )

    class Meta:
        model = Review
        fields = ["reviewer_name", "rating", "comment"]
        widgets = {
            "reviewer_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "comment": forms.Textarea(attrs={"rows": 5}),
        }
