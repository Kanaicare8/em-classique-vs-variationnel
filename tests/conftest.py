"""
Isolation des tests : le calibrage lu par le registre (parametres.valeur) est redirigé vers un dossier vide, de sorte
que les tests utilisent les valeurs provisoires du registre, quelle que soit la machine (sur l'instance, un calibrage
réel ou un essai rapide d'une version antérieure du code peut exister dans resultats/).
"""

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def calibrage_isole(tmp_path_factory):
    ancien = os.environ.get("ICARE_DOSSIER_CALIBRAGE")
    os.environ["ICARE_DOSSIER_CALIBRAGE"] = str(tmp_path_factory.mktemp("calibrage_vide"))
    yield
    if ancien is None:
        os.environ.pop("ICARE_DOSSIER_CALIBRAGE", None)
    else:
        os.environ["ICARE_DOSSIER_CALIBRAGE"] = ancien
