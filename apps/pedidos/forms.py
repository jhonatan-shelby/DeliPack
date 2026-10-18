from django import forms

from .models import Pedido


class PagoForm(forms.Form):
    tipo_entrega = forms.ChoiceField(label="¿Cómo lo recibes?", choices=Pedido.TipoEntrega.choices,
                                     widget=forms.RadioSelect, initial=Pedido.TipoEntrega.OFICINA)
    direccion = forms.CharField(label="Dirección", max_length=200, required=False,
                                widget=forms.TextInput(attrs={"autocomplete": "street-address",
                                                              "placeholder": "Calle, número y sector"}))
    referencia = forms.CharField(label="Referencia", max_length=160, required=False,
                                 widget=forms.TextInput(attrs={"placeholder": "Edificio, piso, oficina o color de la casa"}))
    telefono = forms.CharField(label="Celular de contacto", max_length=20,
                               widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}))
    fecha_entrega = forms.TypedChoiceField(label="Día de entrega", coerce=lambda v: v)
    franja = forms.ChoiceField(label="Horario", choices=Pedido.Franja.choices, widget=forms.RadioSelect,
                               initial=Pedido.Franja.ALMUERZO)
    metodo_pago = forms.ChoiceField(label="Forma de pago", choices=Pedido.MetodoPago.choices,
                                    widget=forms.RadioSelect, initial=Pedido.MetodoPago.EFECTIVO)
    referencia_pago = forms.CharField(label="N.º de comprobante de transferencia (opcional)", max_length=60,
                                      required=False)
    notas = forms.CharField(label="Notas para la cocina (opcional)", max_length=300, required=False,
                            widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Por ejemplo: sin cebolla"}))

    def __init__(self, *args, fechas=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fechas = {f["valor"]: f for f in fechas}
        self.fields["fecha_entrega"].choices = [
            (f["valor"], f"{f['etiqueta']} ({'sin cupos' if f['libres'] == 0 else str(f['libres']) + ' cupos'})")
            for f in fechas
        ]

    def clean_telefono(self):
        tel = self.cleaned_data["telefono"].replace(" ", "")
        if not tel.lstrip("+").isdigit() or not 9 <= len(tel.lstrip("+")) <= 13:
            raise forms.ValidationError("Escribe un número de celular válido, por ejemplo 0991234567.")
        return tel

    def clean_fecha_entrega(self):
        valor = self.cleaned_data["fecha_entrega"]
        f = self.fechas.get(valor)
        if not f:
            raise forms.ValidationError("Elige un día de la lista.")
        if f["libres"] == 0:
            raise forms.ValidationError("Ese día ya no tiene cupos. Elige otro.")
        return f["fecha"]

    def clean(self):
        datos = super().clean()
        if datos.get("tipo_entrega") != Pedido.TipoEntrega.RETIRO and not datos.get("direccion", "").strip():
            self.add_error("direccion", "Escribe la dirección de entrega.")
        return datos
