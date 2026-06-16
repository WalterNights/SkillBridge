"""Tests del módulo `common.skills_taxonomy`.

Verifican el contrato público de la taxonomía única de skills:
  - `normalize` aplica aliases y lowercase
  - `HARD_SKILLS` / `SOFT_SKILLS` / `ALIASES` son consistentes entre sí
  - `all_recognizable` cubre canónicas + aliases
"""
import pytest

from common.skills_taxonomy import (
    ALIASES,
    HARD_SKILLS,
    SOFT_SKILLS,
    all_recognizable,
    normalize,
)


@pytest.mark.unit
class TestNormalize:
    def test_lowercases_and_strips(self):
        assert normalize('  Python  ') == 'python'
        assert normalize('DJANGO') == 'django'

    def test_returns_input_when_no_alias(self):
        assert normalize('python') == 'python'

    @pytest.mark.parametrize('alias,canonical', [
        ('react.js', 'react'),
        ('reactjs', 'react'),
        ('Node.JS', 'node'),
        ('next.js', 'next'),
        ('postgres', 'postgresql'),
        ('c#', 'csharp'),
        ('.net', 'dotnet'),
        ('asp.net', 'aspnet'),
        ('ruby on rails', 'rails'),
        ('golang', 'go'),
        ('google cloud', 'gcp'),
        ('restful', 'rest'),
    ])
    def test_known_aliases_map_to_canonical(self, alias, canonical):
        assert normalize(alias) == canonical

    def test_unknown_skill_passes_through(self):
        assert normalize('haskell') == 'haskell'


@pytest.mark.unit
class TestTaxonomyConsistency:
    def test_all_alias_values_are_canonical_skills(self):
        """Cada valor en ALIASES debe ser una skill canónica conocida.

        Sin esto, normalizar `c#` daría `csharp` pero `csharp` no estaría
        registrado como skill — el matching seguiría fallando.
        """
        canonical_skills = HARD_SKILLS | SOFT_SKILLS
        for alias, canonical in ALIASES.items():
            assert canonical in canonical_skills, (
                f"Alias {alias!r} → {canonical!r}, pero {canonical!r} "
                f"no está en HARD_SKILLS ni SOFT_SKILLS"
            )

    def test_aliases_not_in_canonical_set(self):
        """Los aliases NO deben ser parte del set canónico.

        Si `react.js` está tanto en HARD_SKILLS como en ALIASES,
        normalizar `react.js` da `react` pero el chequeo de pertenencia
        a HARD_SKILLS también daría true para `react.js` directamente,
        generando inconsistencia.
        """
        canonical_skills = HARD_SKILLS | SOFT_SKILLS
        overlap = set(ALIASES.keys()) & canonical_skills
        assert overlap == set(), (
            f"Estos términos están en ambos lados: {overlap}"
        )

    def test_canonical_names_are_lowercase(self):
        for skill in HARD_SKILLS | SOFT_SKILLS:
            assert skill == skill.lower(), f"{skill!r} no está en lowercase"


@pytest.mark.unit
class TestAllRecognizable:
    def test_includes_canonical_and_aliases(self):
        recognized = all_recognizable()
        assert 'react' in recognized       # canónica
        assert 'react.js' in recognized    # alias
        assert 'liderazgo' in recognized   # soft skill
