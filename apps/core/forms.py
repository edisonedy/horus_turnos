"""Base común de formularios del panel.

Antes cada app repetía este mismo __init__ y le ponía `form-control` a TODO,
incluidos los <select> — que en Bootstrap 5 necesitan `form-select` o salen
como una línea plana, sin flecha y con el alto equivocado.
"""
from django import forms


def clase_de_widget(widget):
    """Clase de Bootstrap que le toca a cada tipo de campo."""
    if isinstance(widget, forms.CheckboxInput):
        return 'form-check-input'
    # Select cubre también SelectMultiple y NullBooleanSelect.
    # RadioSelect / CheckboxSelectMultiple NO heredan de Select, así que
    # se quedan con su propio marcado.
    if isinstance(widget, forms.Select):
        return 'form-select'
    return 'form-control'


GUION_POR_DEFECTO = '---------'


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existente = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{existente} {clase_de_widget(field.widget)}'.strip()

            # "---------" no le dice nada a nadie. Si el formulario no puso
            # su propia etiqueta, ponemos una que sí se entienda.
            if isinstance(field, forms.ModelChoiceField):
                if field.empty_label == GUION_POR_DEFECTO:
                    field.empty_label = 'Selecciona…'
            elif isinstance(field, forms.ChoiceField):
                opciones = list(field.choices)
                if opciones and opciones[0][0] in ('', None) and opciones[0][1] == GUION_POR_DEFECTO:
                    opciones[0] = (opciones[0][0], 'Selecciona…')
                    field.choices = opciones
