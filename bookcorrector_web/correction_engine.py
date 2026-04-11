from __future__ import annotations

import re
import unicodedata

from .models import AnalysisResult, Issue


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
    ("de part", "de par", "orthographe", "Locution figee."),
    ("quand a", "quant a", "orthographe", "Locution figee."),
    ("hors mis", "hormis", "orthographe", "La graphie correcte est en un mot."),
    ("sa va", "ça va", "orthographe", "Confusion sa/ça."),
    ("comme ca", "comme ça", "orthographe", "Accent obligatoire."),
    ("tout a fait", "tout à fait", "orthographe", "Accent obligatoire."),
    ("a partir de", "à partir de", "orthographe", "Accent obligatoire."),
    ("en faite", "en fait", "orthographe", "Expression figee."),
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
    ("ainsi que", "ainsi que", "grammaire", "Attention a l'accord."),
    ("quelques choses", "quelque chose", "orthographe", "Toujours singulier."),
    ("il faut que tu fais", "il faut que tu fasses", "grammaire", "Subjonctif obligatoire."),
    ("bien que il est", "bien qu'il soit", "grammaire", "Subjonctif requis."),
    ("avant qu'il part", "avant qu'il parte", "grammaire", "Subjonctif requis."),
    ("pour que il vient", "pour qu'il vienne", "grammaire", "Subjonctif requis."),
    ("j'ai prit", "j'ai pris", "grammaire", "Participe passe incorrect."),
    ("il a mit", "il a mis", "grammaire", "Participe passe incorrect."),
    ("elle a permit", "elle a permis", "grammaire", "Participe passe incorrect."),
    ("il a ouvert", "il a ouvert", "grammaire", "Attention a l'accord selon contexte."),
    ("ce matin la", "ce matin-là", "orthographe", "Trait d'union."),
    ("il ce passe", "il se passe", "orthographe", "Confusion ce/se."),
    ("ce sont passer", "se sont passés", "grammaire", "Accord du participe."),
    ("prevoir a l'avance", "prevoir", "style", "Pleonasme."),
    ("descendre en bas", "descendre", "style", "Pleonasme."),
    ("monter en haut", "monter", "style", "Pleonasme."),
    ("voire meme", "voire", "style", "Redondance."),
    ("collaborer ensemble", "collaborer", "style", "Pleonasme."),
    ("de suite", "tout de suite", "style", "Forme plus soutenue."),
    ("suite a", "a la suite de", "style", "Usage critique."),
    ("par contre", "en revanche", "style", "Registre plus soutenu."),
    ("base sur", "fondé sur", "style", "Anglicisme critique."),
    ("du coup", "", "registre", "Langage oral."),
    ("genre", "", "registre", "Langage familier."),
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
    ("quelque part", "quelque part", "orthographe", "Toujours en deux mots."),
    ("tout les", "tous les", "orthographe", "Accord."),
    ("tout le monde sont", "tout le monde est", "grammaire", "Sujet singulier."),
    ("la plupart est", "la plupart sont", "grammaire", "Souvent pluriel."),
)

MANUAL_REVIEW_NEEDLES = {
    "ainsi que",
    "il a ouvert",
    "du coup",
    "genre",
    "en mode",
    "amener quelqu'un",
    "emmener quelque chose",
    "apporter quelqu'un",
    "ramener quelque chose",
    "je m'excuse",
    "quelque part",
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


class CorrectionEngine:
    def analyze(self, text: str) -> AnalysisResult:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        warnings: list[str] = []
        if not normalized:
            warnings.append("Le document ne contient pas de texte exploitable.")
            return AnalysisResult(original_text="", warnings=warnings)

        issues = []
        issues.extend(self._collect_exact_replacements(normalized))
        issues.extend(self._collect_typography_issues(normalized))
        issues.extend(self._collect_sentence_style_issues(normalized))
        issues.extend(self._collect_style_patterns(normalized))

        deduped = self._deduplicate(issues)
        deduped.sort(key=lambda issue: (issue.start, issue.end, issue.category))
        return AnalysisResult(original_text=normalized, issues=deduped, warnings=warnings)

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
                suggestion = normalized_replacement or "Verification manuelle recommandee selon le contexte."
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

    def _collect_typography_issues(self, text: str) -> list[Issue]:
        issues: list[Issue] = []
        next_id = 1000

        for match in DOUBLE_SPACES.finditer(text):
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
