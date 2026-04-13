from __future__ import annotations

import pathlib
import re
import unicodedata

from .models import AnalysisResult, Issue

try:
    from spellchecker import SpellChecker

    SPELLCHECKER_AVAILABLE = True
except ImportError:
    SpellChecker = None
    SPELLCHECKER_AVAILABLE = False


WORD_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[’'-][A-Za-zÀ-ÖØ-öø-ÿ]+)*")
SENTENCE_PATTERN = re.compile(r"[^.!?…]+[.!?…]*", re.MULTILINE)
DOUBLE_SPACES = re.compile(r" {2,}")
BAD_COMMA_SPACING = re.compile(r"\s+,")
MISSING_SPACE_AFTER_PUNCT = re.compile(r"([,;:!?])([^\s»])")
MISSING_SPACE_BEFORE_DOUBLE_PUNCT = re.compile(r"([^\s«])([;:!?])")
ELLIPSIS_THREE_DOTS = re.compile(r"\.\.\.")
REPEATED_PUNCT = re.compile(r"([!?])\1{1,}")
STRAIGHT_APOSTROPHE = re.compile(r"([A-Za-zÀ-ÖØ-öø-ÿ])'([A-Za-zÀ-ÖØ-öø-ÿ])")
DOUBLE_WORD = re.compile(r"\b([A-Za-zÀ-ÖØ-öø-ÿ]{2,})\s+\1\b", re.IGNORECASE)
TOKEN_PART_SPLIT = re.compile(r"([’'-])")
JE_CEST_PATTERN = re.compile(r"\bje\s+c['’]?est\b", re.IGNORECASE)
SA_A_PATTERN = re.compile(r"\bsa\s+a\b", re.IGNORECASE)
SA_SE_PATTERN = re.compile(r"\bsa\s+se\b", re.IGNORECASE)
IL_ONT_PATTERN = re.compile(r"\bil\s+ont\b", re.IGNORECASE)
ELLE_ONT_PATTERN = re.compile(r"\belle\s+ont\b", re.IGNORECASE)
AUXILIARY_FORMS_PATTERN = (
    r"ai|as|a|avons|avez|ont|avais|avait|avions|aviez|avaient|"
    r"aurai|auras|aura|aurons|aurez|auront|"
    r"suis|es|est|sommes|etes|sont|"
    r"serai|seras|sera|serons|serez|seront|"
    r"étais|était|étions|étiez|étaient|"
    r"etais|etait|etions|etiez|etaient"
)
AUXILIARY_ER_PATTERN = re.compile(
    rf"\b(?P<aux>{AUXILIARY_FORMS_PATTERN})\s+(?P<lemma>[A-Za-zÀ-ÖØ-öø-ÿ]{{3,}}er)\b",
    re.IGNORECASE,
)
AUXILIARY_PRIT_PATTERN = re.compile(rf"\b(?P<aux>{AUXILIARY_FORMS_PATTERN})\s+prit\b", re.IGNORECASE)
AUXILIARY_MIT_PATTERN = re.compile(rf"\b(?P<aux>{AUXILIARY_FORMS_PATTERN})\s+mit\b", re.IGNORECASE)
AUXILIARY_PERMIT_PATTERN = re.compile(rf"\b(?P<aux>{AUXILIARY_FORMS_PATTERN})\s+permit\b", re.IGNORECASE)
SA_A_ER_PATTERN = re.compile(r"\bsa\s+a\s+(?P<lemma>[A-Za-zÀ-ÖØ-öø-ÿ]{3,}er)\b", re.IGNORECASE)
IL_ONT_ER_PATTERN = re.compile(r"\bil\s+ont\s+(?P<lemma>[A-Za-zÀ-ÖØ-öø-ÿ]{3,}er)\b", re.IGNORECASE)
ELLE_ONT_ER_PATTERN = re.compile(r"\belle\s+ont\s+(?P<lemma>[A-Za-zÀ-ÖØ-öø-ÿ]{3,}er)\b", re.IGNORECASE)
IL_ONT_PRIT_PATTERN = re.compile(r"\bil\s+ont\s+prit\b", re.IGNORECASE)
ELLE_ONT_PRIT_PATTERN = re.compile(r"\belle\s+ont\s+prit\b", re.IGNORECASE)
IL_ONT_MIT_PATTERN = re.compile(r"\bil\s+ont\s+mit\b", re.IGNORECASE)
ELLE_ONT_MIT_PATTERN = re.compile(r"\belle\s+ont\s+mit\b", re.IGNORECASE)

STOP_WORDS = {
    "a",
    "au",
    "aux",
    "ce",
    "ces",
    "dans",
    "de",
    "des",
    "du",
    "elle",
    "elles",
    "en",
    "et",
    "il",
    "ils",
    "je",
    "la",
    "le",
    "les",
    "leur",
    "lui",
    "mais",
    "me",
    "mon",
    "ne",
    "nous",
    "on",
    "ou",
    "par",
    "pas",
    "pour",
    "que",
    "qui",
    "se",
    "ses",
    "son",
    "sur",
    "te",
    "tu",
    "un",
    "une",
    "vous",
    "y",
}

EXACT_REPLACEMENTS = (
    ("quelque soit", "quel que soit", "grammaire", "Expression fautive courante."),
    ("voir meme", "voire même", "orthographe", "La bonne graphie est 'voire'."),
    ("soit disant", "soi-disant", "orthographe", "La graphie correcte est avec trait d'union."),
    ("comme meme", "quand même", "orthographe", "Expression fautive courante."),
    ("malgre que", "bien que", "grammaire", "Forme fautive."),
    ("au jour d'aujourd'hui", "aujourd'hui", "style", "Expression redondante."),
    ("a l'heure d'aujourd'hui", "aujourd'hui", "style", "Redondance."),
    ("d'avantage", "davantage", "orthographe", "Mot souvent confondu."),
    ("de part", "de par", "orthographe", "Locution figée."),
    ("quand a", "quant à", "orthographe", "Locution figée."),
    ("hors mis", "hormis", "orthographe", "La graphie correcte est en un mot."),
    ("sa va", "ça va", "orthographe", "Confusion sa/ça."),
    ("comme ca", "comme ça", "orthographe", "Accent obligatoire."),
    ("tout a fait", "tout à fait", "orthographe", "Accent obligatoire."),
    ("a partir de", "à partir de", "orthographe", "Accent obligatoire."),
    ("en faite", "en fait", "orthographe", "Expression figée."),
    ("il y a t'il", "y a-t-il", "orthographe", "Forme interrogative avec trait d'union."),
    ("c'est des", "ce sont des", "grammaire", "Forme correcte."),
    ("pres de", "près de", "orthographe", "Accent sur 'près'."),
    ("plutot", "plutôt", "orthographe", "Accent circonflexe."),
    ("tres", "très", "orthographe", "Accent obligatoire."),
    ("des fois", "parfois", "style", "Formulation plus correcte."),
    ("au final", "finalement", "style", "Usage familier."),
    ("a cause que", "parce que", "grammaire", "Forme incorrecte."),
    ("malgres", "malgré", "orthographe", "Pas de 's'."),
    ("parmis", "parmi", "orthographe", "Pas de 's'."),
    ("quelques choses", "quelque chose", "orthographe", "Toujours singulier."),
    ("il faut que tu fais", "il faut que tu fasses", "grammaire", "Subjonctif obligatoire."),
    ("bien que il est", "bien qu'il soit", "grammaire", "Subjonctif requis."),
    ("avant qu'il part", "avant qu'il parte", "grammaire", "Subjonctif requis."),
    ("pour que il vient", "pour qu'il vienne", "grammaire", "Subjonctif requis."),
    ("j'ai prit", "j'ai pris", "grammaire", "Participe passé incorrect."),
    ("il a mit", "il a mis", "grammaire", "Participe passé incorrect."),
    ("elle a permit", "elle a permis", "grammaire", "Participe passé incorrect."),
    ("ce matin la", "ce matin-là", "orthographe", "Trait d'union."),
    ("il ce passe", "il se passe", "orthographe", "Confusion ce/se."),
    ("ce sont passer", "se sont passés", "grammaire", "Accord du participe."),
    ("prevoir a l'avance", "prévoir", "style", "Pléonasme."),
    ("descendre en bas", "descendre", "style", "Pléonasme."),
    ("monter en haut", "monter", "style", "Pléonasme."),
    ("voire meme", "voire", "style", "Redondance."),
    ("collaborer ensemble", "collaborer", "style", "Pléonasme."),
    ("de suite", "tout de suite", "style", "Forme plus soutenue."),
    ("suite a", "à la suite de", "style", "Usage critiqué."),
    ("par contre", "en revanche", "style", "Registre plus soutenu."),
    ("base sur", "fondé sur", "style", "Anglicisme critiqué."),
    ("du coup", "", "registre", "Langage oral."),
    ("en mode", "", "registre", "Langage familier."),
    ("amener quelqu'un", "emmener quelqu'un", "grammaire", "Difference de sens."),
    ("emmener quelque chose", "amener quelque chose", "grammaire", "Difference de sens."),
    ("apporter quelqu'un", "emmener quelqu'un", "grammaire", "Erreur frequente."),
    ("ramener quelque chose", "rapporter quelque chose", "grammaire", "Difference de sens."),
    ("apres que il soit", "après qu'il est", "grammaire", "Indicatif obligatoire."),
    ("si j'aurais", "si j'avais", "grammaire", "Conditionnel interdit apres 'si'."),
    ("je m'excuse", "je vous prie de m'excuser", "style", "Forme plus correcte."),
    ("je vous pris", "je vous prie", "orthographe", "Forme correcte."),
    ("cordialement bien a vous", "bien à vous", "style", "Formule simplifiée."),
    ("tout les", "tous les", "orthographe", "Accord."),
    ("tout le monde sont", "tout le monde est", "grammaire", "Sujet singulier."),
    ("la plupart est", "la plupart sont", "grammaire", "Souvent pluriel."),
)

MANUAL_REVIEW_NEEDLES = {
    "du coup",
    "en mode",
    "amener quelqu'un",
    "emmener quelque chose",
    "apporter quelqu'un",
    "ramener quelque chose",
    "je m'excuse",
    "suite a",
    "par contre",
    "base sur",
    "des fois",
    "au final",
}

STYLE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bil y a\b", re.IGNORECASE),
        "Tournure faible. Une formulation plus directe est souvent possible.",
    ),
    (
        re.compile(r"\bau niveau de\b", re.IGNORECASE),
        "Expression souvent lourde. Remplace-la par un terme plus precis si possible.",
    ),
    (
        re.compile(r"\bdans le cadre de\b", re.IGNORECASE),
        "Tournure administrative. Elle peut souvent etre simplifiee.",
    ),
    (
        re.compile(r"\bafin de pouvoir\b", re.IGNORECASE),
        "Formulation redondante. 'Pour' suffit souvent.",
    ),
    (
        re.compile(r"\bforce est de constater\b", re.IGNORECASE),
        "Expression tres marquee. Verifie si elle sert vraiment le ton du texte.",
    ),
    (
        re.compile(r"\bvraiment\b", re.IGNORECASE),
        "Intensifieur frequent. A utiliser avec parcimonie.",
    ),
    (
        re.compile(r"\btres\b", re.IGNORECASE),
        "Intensifieur frequent. Une image plus concrete est parfois plus forte.",
    ),
)

SPELLING_PREFIX_PARTS = {"c", "d", "j", "l", "m", "n", "qu", "s", "t"}
SPELLING_MIN_LENGTH = 4
CUSTOM_WORDS_PATH = pathlib.Path(__file__).resolve().parent / "resources" / "custom_words_fr.txt"


class CorrectionEngine:
    def __init__(self) -> None:
        self._spellchecker = self._build_spellchecker()

    def analyze(self, text: str) -> AnalysisResult:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        warnings: list[str] = []
        if not normalized:
            warnings.append("Le document ne contient pas de texte exploitable.")
            return AnalysisResult(original_text="", warnings=warnings)

        issues = []
        exact_issues = self._collect_exact_replacements(normalized)
        contextual_issues = self._collect_contextual_replacements(normalized)
        protected_ranges = [
            (issue.start, issue.end)
            for issue in [*exact_issues, *contextual_issues]
            if issue.category in {"orthographe", "grammaire"}
        ]
        issues.extend(exact_issues)
        issues.extend(contextual_issues)
        spelling_issues = self._collect_spelling_issues(normalized, protected_ranges, warnings)
        issues.extend(spelling_issues)
        language_ranges = [
            (issue.start, issue.end)
            for issue in [*exact_issues, *contextual_issues, *spelling_issues]
            if issue.category in {"orthographe", "grammaire"}
        ]
        issues.extend(self._collect_typography_issues(normalized, language_ranges))
        issues.extend(self._collect_sentence_style_issues(normalized))
        issues.extend(self._collect_style_patterns(normalized))

        deduped = self._deduplicate(issues)
        deduped.sort(key=lambda issue: (issue.start, issue.end, issue.category))
        return AnalysisResult(original_text=normalized, issues=deduped, warnings=warnings)

    def _build_spellchecker(self):
        if not SPELLCHECKER_AVAILABLE:
            return None

        spellchecker = SpellChecker(language="fr", distance=1)
        if CUSTOM_WORDS_PATH.exists():
            custom_words = [
                line.strip()
                for line in CUSTOM_WORDS_PATH.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            if custom_words:
                spellchecker.word_frequency.load_words(custom_words)
        return spellchecker

    def _collect_exact_replacements(self, text: str) -> list[Issue]:
        issues: list[Issue] = []
        next_id = 1
        normalized_text = _normalize_for_exact_match(text)
        for needle, replacement, category, message in EXACT_REPLACEMENTS:
            normalized_needle = _normalize_for_exact_match(needle)
            pattern = re.compile(rf"(?<!\w){re.escape(normalized_needle)}(?!\w)", re.IGNORECASE)
            for match in pattern.finditer(normalized_text):
                index = match.start()
                end = match.end()
                excerpt = text[index:end]
                normalized_replacement = replacement.strip() or None
                has_real_replacement = bool(
                    normalized_replacement
                    and _normalize_for_display_comparison(excerpt)
                    != _normalize_for_display_comparison(normalized_replacement)
                )
                should_default_select = has_real_replacement and (
                    category in {"orthographe", "grammaire"}
                    and normalized_needle not in MANUAL_REVIEW_NEEDLES
                )
                suggestion = normalized_replacement or "Vérification manuelle recommandée selon le contexte."
                issues.append(
                    Issue(
                        issue_id=f"issue-{next_id}",
                        category=category,
                        message=message,
                        excerpt=excerpt,
                        start=index,
                        end=end,
                        source="regle-locale",
                        suggestion=suggestion,
                        severity=_severity_for_category(category, should_default_select),
                        confidence=0.93,
                        replacement=_match_case(excerpt, normalized_replacement) if has_real_replacement else None,
                        default_selected=should_default_select,
                    )
                )
                next_id += 1
        return issues

    def _collect_contextual_replacements(self, text: str) -> list[Issue]:
        issues: list[Issue] = []
        next_id = 250

        def add_issue(
            match: re.Match[str],
            replacement: str,
            category: str,
            message: str,
            confidence: float = 0.88,
        ) -> None:
            nonlocal next_id
            start = match.start()
            end = match.end()
            if _range_overlaps(start, end, [(issue.start, issue.end) for issue in issues]):
                return

            excerpt = text[start:end]
            fixed = _match_case(excerpt, replacement)
            issues.append(
                Issue(
                    issue_id=f"issue-{next_id}",
                    category=category,
                    message=message,
                    excerpt=excerpt,
                    start=start,
                    end=end,
                    source="regle-contextuelle",
                    suggestion=fixed,
                    severity=_severity_for_category(category, True),
                    confidence=confidence,
                    replacement=fixed,
                    default_selected=True,
                )
            )
            next_id += 1

        for match in SA_A_ER_PATTERN.finditer(text):
            lemma = match.group("lemma")
            add_issue(
                match,
                f"ça a {_infinitive_to_past_participle(lemma)}",
                "grammaire",
                "Apres 'a', on attend generalement un participe passe.",
                0.94,
            )

        for match in IL_ONT_ER_PATTERN.finditer(text):
            lemma = match.group("lemma")
            add_issue(
                match,
                f"ils ont {_infinitive_to_past_participle(lemma)}",
                "grammaire",
                "Le sujet pluriel et le participe passe semblent attendus ici.",
                0.93,
            )

        for match in ELLE_ONT_ER_PATTERN.finditer(text):
            lemma = match.group("lemma")
            add_issue(
                match,
                f"elles ont {_infinitive_to_past_participle(lemma)}",
                "grammaire",
                "Le sujet pluriel et le participe passe semblent attendus ici.",
                0.93,
            )

        for pattern, replacement in (
            (IL_ONT_PRIT_PATTERN, "ils ont pris"),
            (ELLE_ONT_PRIT_PATTERN, "elles ont pris"),
            (IL_ONT_MIT_PATTERN, "ils ont mis"),
            (ELLE_ONT_MIT_PATTERN, "elles ont mis"),
        ):
            for match in pattern.finditer(text):
                add_issue(
                    match,
                    replacement,
                    "grammaire",
                    "Le sujet pluriel et le participe passe semblent attendus ici.",
                    0.95,
                )

        for match in AUXILIARY_ER_PATTERN.finditer(text):
            aux = match.group("aux")
            lemma = match.group("lemma")
            add_issue(
                match,
                f"{aux} {_infinitive_to_past_participle(lemma)}",
                "grammaire",
                "Apres un auxiliaire, on attend generalement un participe passe.",
                0.87,
            )

        for pattern, corrected_participle in (
            (AUXILIARY_PRIT_PATTERN, "pris"),
            (AUXILIARY_MIT_PATTERN, "mis"),
            (AUXILIARY_PERMIT_PATTERN, "permis"),
        ):
            for match in pattern.finditer(text):
                aux = match.group("aux")
                add_issue(
                    match,
                    f"{aux} {corrected_participle}",
                    "grammaire",
                    "Participe passe incorrect apres auxiliaire.",
                    0.92,
                )

        for pattern, replacement, category, message, confidence in (
            (JE_CEST_PATTERN, "je sais", "grammaire", "Confusion entre 'c'est' et le verbe savoir.", 0.96),
            (SA_A_PATTERN, "ça a", "orthographe", "Confusion frequente entre 'sa' et 'ca'.", 0.96),
            (SA_SE_PATTERN, "ça se", "orthographe", "Confusion frequente entre 'sa' et 'ca'.", 0.95),
            (IL_ONT_PATTERN, "ils ont", "grammaire", "Le sujet pluriel semble attendu ici.", 0.84),
            (ELLE_ONT_PATTERN, "elles ont", "grammaire", "Le sujet pluriel semble attendu ici.", 0.84),
        ):
            for match in pattern.finditer(text):
                add_issue(match, replacement, category, message, confidence)

        return issues

    def _collect_spelling_issues(
        self,
        text: str,
        protected_ranges: list[tuple[int, int]],
        warnings: list[str],
    ) -> list[Issue]:
        spellchecker = self._spellchecker
        if spellchecker is None:
            warnings.append(
                "Le dictionnaire orthographique avance n'est pas disponible dans cet environnement. "
                "L'analyse orthographique restera limitee aux regles explicites."
            )
            return []

        issues: list[Issue] = []
        next_id = 500
        for match in WORD_PATTERN.finditer(text):
            token = match.group(0)
            start = match.start()
            end = match.end()

            if _range_overlaps(start, end, protected_ranges):
                continue
            if self._should_skip_spelling_token(token, text, start):
                continue

            suggestion_payload = self._build_spelling_suggestion(token, spellchecker)
            if suggestion_payload is None:
                continue

            replacement, suggestions = suggestion_payload
            safe_auto_apply = bool(replacement and _is_safe_spelling_replacement(token, replacement))
            issues.append(
                Issue(
                    issue_id=f"issue-{next_id}",
                    category="orthographe",
                    message="Mot potentiellement mal orthographie.",
                    excerpt=token,
                    start=start,
                    end=end,
                    source="dictionnaire-fr",
                    suggestion=", ".join(suggestions) if suggestions else "Verification manuelle recommandee.",
                    severity="haute" if safe_auto_apply else "moyenne",
                    confidence=0.9 if safe_auto_apply else 0.68,
                    replacement=replacement,
                    default_selected=safe_auto_apply,
                )
            )
            next_id += 1

        return issues

    def _should_skip_spelling_token(self, token: str, text: str, start: int) -> bool:
        plain = _normalize_for_exact_match(token)
        alpha_length = sum(1 for char in plain if char.isalpha())
        if alpha_length < SPELLING_MIN_LENGTH and "’" not in token and "'" not in token and "-" not in token:
            return True
        if token.isupper():
            return True
        if plain in STOP_WORDS:
            return True
        if _is_likely_proper_noun(token, text, start):
            return True
        return False

    def _build_spelling_suggestion(self, token: str, spellchecker) -> tuple[str | None, list[str]] | None:
        if any(separator in token for separator in ("’", "'", "-")):
            return self._build_compound_spelling_suggestion(token, spellchecker)
        return self._build_simple_spelling_suggestion(token, spellchecker)

    def _build_simple_spelling_suggestion(self, token: str, spellchecker) -> tuple[str | None, list[str]] | None:
        normalized = _normalize_for_display_comparison(token)
        if normalized in spellchecker:
            return None

        ordered = _rank_spellchecker_candidates(spellchecker, normalized)
        if not ordered:
            return None

        replacement = _match_case(token, ordered[0])
        suggestions = [_match_case(token, suggestion) for suggestion in ordered[:3]]
        return replacement, suggestions

    def _build_compound_spelling_suggestion(self, token: str, spellchecker) -> tuple[str | None, list[str]] | None:
        parts = TOKEN_PART_SPLIT.split(token)
        changed = False
        corrected_parts: list[str] = []
        all_suggestions: list[str] = []

        for index, part in enumerate(parts):
            if not part or TOKEN_PART_SPLIT.fullmatch(part):
                corrected_parts.append(part)
                continue

            normalized_part = _normalize_for_display_comparison(part)
            previous_part = parts[index - 1] if index > 0 else ""
            if previous_part in {"’", "'"} and normalized_part and len(_normalize_for_exact_match(part)) > 1:
                prefix = _normalize_for_exact_match(parts[index - 2]) if index >= 2 else ""
                if prefix in SPELLING_PREFIX_PARTS:
                    corrected_parts.append(part)
                    continue

            if len(_normalize_for_exact_match(part)) < SPELLING_MIN_LENGTH:
                corrected_parts.append(part)
                continue
            if normalized_part in self._spellchecker:
                corrected_parts.append(part)
                continue

            ordered = _rank_spellchecker_candidates(spellchecker, normalized_part)
            if not ordered:
                corrected_parts.append(part)
                continue

            corrected = _match_case(part, ordered[0])
            corrected_parts.append(corrected)
            all_suggestions.extend(_match_case(part, suggestion) for suggestion in ordered[:2])
            changed = True

        if not changed:
            return None

        replacement = "".join(corrected_parts)
        return replacement, [replacement, *all_suggestions]

    def _collect_typography_issues(self, text: str, protected_ranges: list[tuple[int, int]]) -> list[Issue]:
        issues: list[Issue] = []
        next_id = 1000

        for match in DOUBLE_SPACES.finditer(text):
            if _range_overlaps(match.start(), match.end(), protected_ranges):
                continue
            issues.append(
                Issue(
                    issue_id=f"issue-{next_id}",
                    category="typographie",
                    message="Espaces multiples detectees.",
                    excerpt=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    source="regle-locale",
                    suggestion="Remplacer par un seul espace.",
                    severity="faible",
                    confidence=0.99,
                    replacement=" ",
                    default_selected=True,
                )
            )
            next_id += 1

        for match in BAD_COMMA_SPACING.finditer(text):
            if _range_overlaps(match.start(), match.end(), protected_ranges):
                continue
            issues.append(
                Issue(
                    issue_id=f"issue-{next_id}",
                    category="typographie",
                    message="Espace inutile avant une virgule.",
                    excerpt=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    source="regle-locale",
                    suggestion="Retirer l'espace avant la virgule.",
                    severity="faible",
                    confidence=0.99,
                    replacement=",",
                    default_selected=True,
                )
            )
            next_id += 1

        for match in MISSING_SPACE_AFTER_PUNCT.finditer(text):
            if _range_overlaps(match.start(), match.end(), protected_ranges):
                continue
            replacement = f"{match.group(1)} {match.group(2)}"
            issues.append(
                Issue(
                    issue_id=f"issue-{next_id}",
                    category="typographie",
                    message="Ponctuation collee au mot suivant.",
                    excerpt=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    source="regle-locale",
                    suggestion="Ajouter un espace apres la ponctuation.",
                    severity="faible",
                    confidence=0.96,
                    replacement=replacement,
                    default_selected=True,
                )
            )
            next_id += 1

        for match in MISSING_SPACE_BEFORE_DOUBLE_PUNCT.finditer(text):
            if _range_overlaps(match.start(), match.end(), protected_ranges):
                continue
            if match.group(1) == "\n":
                continue
            replacement = f"{match.group(1)} {match.group(2)}"
            issues.append(
                Issue(
                    issue_id=f"issue-{next_id}",
                    category="typographie",
                    message="Ponctuation haute sans espace avant.",
                    excerpt=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    source="regle-locale",
                    suggestion="Ajouter un espace avant ce signe en composition francaise.",
                    severity="faible",
                    confidence=0.8,
                    replacement=replacement,
                    default_selected=False,
                )
            )
            next_id += 1

        for match in ELLIPSIS_THREE_DOTS.finditer(text):
            if _range_overlaps(match.start(), match.end(), protected_ranges):
                continue
            issues.append(
                Issue(
                    issue_id=f"issue-{next_id}",
                    category="typographie",
                    message="Trois points consecutifs detectes.",
                    excerpt=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    source="regle-locale",
                    suggestion="Remplacer par le caractere d'ellipse.",
                    severity="faible",
                    confidence=0.88,
                    replacement="…",
                    default_selected=True,
                )
            )
            next_id += 1

        for match in STRAIGHT_APOSTROPHE.finditer(text):
            if _range_overlaps(match.start(), match.end(), protected_ranges):
                continue
            replacement = f"{match.group(1)}’{match.group(2)}"
            issues.append(
                Issue(
                    issue_id=f"issue-{next_id}",
                    category="typographie",
                    message="Apostrophe droite detectee.",
                    excerpt=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    source="regle-locale",
                    suggestion="Remplacer par une apostrophe typographique.",
                    severity="faible",
                    confidence=0.86,
                    replacement=replacement,
                    default_selected=True,
                )
            )
            next_id += 1

        return issues

    def _collect_sentence_style_issues(self, text: str) -> list[Issue]:
        issues: list[Issue] = []
        next_id = 2000

        for match in DOUBLE_WORD.finditer(text):
            issues.append(
                Issue(
                    issue_id=f"issue-{next_id}",
                    category="grammaire",
                    message="Mot repete consecutivement.",
                    excerpt=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    source="regle-locale",
                    suggestion=match.group(1),
                    severity="moyenne",
                    confidence=0.95,
                    replacement=match.group(1),
                    default_selected=True,
                )
            )
            next_id += 1

        for sentence_match in SENTENCE_PATTERN.finditer(text):
            sentence = sentence_match.group(0).strip()
            if not sentence:
                continue
            sentence_start = sentence_match.start()
            words = list(WORD_PATTERN.finditer(sentence))

            if len(words) > 34:
                issues.append(
                    Issue(
                        issue_id=f"issue-{next_id}",
                        category="style",
                        message="Phrase tres longue.",
                        excerpt=sentence[:180],
                        start=sentence_start,
                        end=sentence_match.end(),
                        source="regle-locale",
                        suggestion="Envisage de couper la phrase pour alleger le rythme.",
                        severity="moyenne",
                        confidence=0.74,
                    )
                )
                next_id += 1

            adverbs = [word.group(0) for word in words if word.group(0).lower().endswith("ment") and len(word.group(0)) > 6]
            if len(adverbs) >= 3:
                issues.append(
                    Issue(
                        issue_id=f"issue-{next_id}",
                        category="style",
                        message="Concentration d'adverbes en -ment.",
                        excerpt=sentence[:180],
                        start=sentence_start,
                        end=sentence_match.end(),
                        source="regle-locale",
                        suggestion="Le passage peut gagner en nettete avec des verbes plus precis.",
                        severity="moyenne",
                        confidence=0.66,
                    )
                )
                next_id += 1

            seen: dict[str, int] = {}
            for word in words:
                token = word.group(0).lower()
                if len(token) < 4 or token in STOP_WORDS:
                    continue
                seen[token] = seen.get(token, 0) + 1
                if seen[token] == 2:
                    issues.append(
                        Issue(
                            issue_id=f"issue-{next_id}",
                            category="style",
                            message="Mot repete dans la meme phrase.",
                            excerpt=word.group(0),
                            start=sentence_start + word.start(),
                            end=sentence_start + word.end(),
                            source="regle-locale",
                            suggestion="Verifie si cette repetition est voulue.",
                            severity="faible",
                            confidence=0.68,
                        )
                    )
                    next_id += 1

        for match in REPEATED_PUNCT.finditer(text):
            issues.append(
                Issue(
                    issue_id=f"issue-{next_id}",
                    category="style",
                    message="Ponctuation expressive repetee.",
                    excerpt=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    source="regle-locale",
                    suggestion="A utiliser avec parcimonie pour garder son impact.",
                    severity="faible",
                    confidence=0.67,
                )
            )
            next_id += 1

        return issues

    def _collect_style_patterns(self, text: str) -> list[Issue]:
        issues: list[Issue] = []
        next_id = 3000
        for pattern, suggestion in STYLE_PATTERNS:
            for match in pattern.finditer(text):
                issues.append(
                    Issue(
                        issue_id=f"issue-{next_id}",
                        category="style",
                        message="Tournure a revoir.",
                        excerpt=match.group(0),
                        start=match.start(),
                        end=match.end(),
                        source="regle-locale",
                        suggestion=suggestion,
                        severity="faible",
                        confidence=0.62,
                    )
                )
                next_id += 1
        return issues

    def _deduplicate(self, issues: list[Issue]) -> list[Issue]:
        unique: dict[tuple[int, int, str, str], Issue] = {}
        for issue in issues:
            key = (issue.start, issue.end, issue.category, issue.message)
            current = unique.get(key)
            if current is None or issue.confidence > current.confidence:
                unique[key] = issue
        return list(unique.values())


def _match_case(source: str, replacement: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _normalize_for_exact_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    stripped = "".join(char for char in normalized if not unicodedata.combining(char))
    return stripped.replace("’", "'").lower()


def _severity_for_category(category: str, should_default_select: bool) -> str:
    if category == "orthographe":
        return "haute"
    if category == "grammaire":
        return "haute" if should_default_select else "moyenne"
    if category == "registre":
        return "faible"
    if category == "style":
        return "moyenne"
    return "faible"


def _normalize_for_display_comparison(value: str) -> str:
    return value.replace("’", "'").lower()


def _range_overlaps(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(not (end <= range_start or start >= range_end) for range_start, range_end in ranges)


def _is_likely_proper_noun(token: str, text: str, start: int) -> bool:
    if not token[:1].isupper():
        return False
    cursor = start - 1
    while cursor >= 0 and text[cursor].isspace():
        cursor -= 1
    if cursor < 0:
        return False
    return text[cursor] not in ".!?\n:;«"


def _rank_spellchecker_candidates(spellchecker, word: str) -> list[str]:
    candidates = spellchecker.candidates(word)
    if not candidates:
        return []
    return sorted(
        candidates,
        key=lambda candidate: (
            -spellchecker.word_usage_frequency(candidate),
            _levenshtein_distance(word, candidate),
            candidate,
        ),
    )


def _is_safe_spelling_replacement(source: str, replacement: str) -> bool:
    display_source = _normalize_for_display_comparison(source)
    display_replacement = _normalize_for_display_comparison(replacement)
    normalized_source = _normalize_for_exact_match(source)
    normalized_replacement = _normalize_for_exact_match(replacement)
    if display_source == display_replacement:
        return False
    if normalized_source == normalized_replacement:
        return True
    if normalized_source[:1] != normalized_replacement[:1]:
        return False
    if len(normalized_source) >= 5 and len(normalized_replacement) >= 5:
        if normalized_source[:2] != normalized_replacement[:2]:
            return False
    return _levenshtein_distance(normalized_source, normalized_replacement) <= 2


def _levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            insertion = current[right_index - 1] + 1
            deletion = previous[right_index] + 1
            substitution = previous[right_index - 1] + (left_char != right_char)
            current.append(min(insertion, deletion, substitution))
        previous = current
    return previous[-1]


def _infinitive_to_past_participle(verb: str) -> str:
    lowered = _normalize_for_display_comparison(verb)
    if not lowered.endswith("er"):
        return verb
    return _match_case(verb, lowered[:-2] + "é")
