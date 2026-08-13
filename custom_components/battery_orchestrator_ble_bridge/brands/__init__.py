"""
Registro de marcas soportadas por el puente. Sumar una marca nueva es
anadir su entrada aqui (y su carpeta `brands/<marca>/` con un adaptador
que cumpla `brands.base.BrandAdapter`) — nada mas de este repositorio
necesita cambiar, y Battery Orchestrator solo tiene que empezar a mandar
`"brand": "<marca>"` en sus llamadas a los servicios de siempre.
"""

from __future__ import annotations

from .base import BrandAdapter
from .ecoflow.adapter import EcoflowBrandAdapter

BRANDS: dict[str, BrandAdapter] = {
    "ecoflow": EcoflowBrandAdapter(),
}
