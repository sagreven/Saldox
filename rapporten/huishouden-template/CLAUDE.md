# Huishouden-template: instructies voor Claude Code

- **Saldox is de adviserende partij.** Schrijf vanuit Saldox als adviseur, met "u". Geen voorbehouden of disclaimers die afstand nemen van het advies.
- **Prijzen van de klant** (panelen, batterijset, omvormer) worden niet ter discussie gesteld.
- Alle getallen in de tekst komen uit het rekenmodel; pas nooit een getal in een `.md` met de hand aan, maar de invoer in `build_huis.py` of `model_huis.py`, en draai daarna `python3 build_huis.py && python3 check_huis.py`.
- Bedragen voor huishoudens altijd incl. btw tonen (excl. btw in de begroting ernaast). Zonnepanelen 0% (nultarief), batterij en laadpaal 21%.
- **Inkoopprijzen** die de gebruiker opgeeft, gaan eerst in `../prijzen/inkoopprijzen.json` en `.md`; de templates lezen ze daaruit via `inkoop()`/`bedrag()`. Prijzen die niet zijn opgegeven, staan als "Marktprijs" of "Stelpost" in de begroting.
