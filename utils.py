from natasha import (
    Segmenter,
    MorphVocab,

    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,

    PER,
    LOC,
    ORG,

    Doc
)
import pandas as pd
import numpy as np
import ast

# Инициализация компонентов Natasha
segmenter = Segmenter()
morph_vocab = MorphVocab()

emb = NewsEmbedding()
morph_tagger = NewsMorphTagger(emb)
syntax_parser = NewsSyntaxParser(emb)
ner_tagger = NewsNERTagger(emb)


def extract_entities_natasha(text):
    """Извлечение сущностей с помощью Natasha"""

    # Создаем документ и применяем все обработчики
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_morph(morph_tagger)
    doc.parse_syntax(syntax_parser)
    doc.tag_ner(ner_tagger)

    # Извлекаем сущности
    persons = []
    organizations = []
    locations = []

    for span in doc.spans:
        span.normalize(morph_vocab)

        if span.type == PER:
            persons.append(span.normal)
        elif span.type == ORG:
            organizations.append(span.normal)
        elif span.type == LOC:
            locations.append(span.normal)

    return {
        'persons': list(set(persons)),
        'organizations': list(set(organizations)),
        'locations': list(set([l.lower() for l in locations if l]))
    }

def extract_countries_from_locations_simple(locations_data, lemma_to_country):
    """
    Упрощенная версия для быстрой обработки
    """
    # Создаем словарь в нижнем регистре
    lemma_lower = {k.lower(): v for k, v in lemma_to_country.items()}

    # Быстрая проверка на пустые значения
    if not locations_data or (isinstance(locations_data, str) and not locations_data.strip()):
        return []

    countries = []

    # Обработка строк
    if isinstance(locations_data, str):
        # Пробуем распарсить как список
        if locations_data.startswith('[') and locations_data.endswith(']'):
            try:
                loc_list = ast.literal_eval(locations_data)
                if isinstance(loc_list, list):
                    for loc in loc_list:
                        loc_lower = str(loc).strip().lower()
                        if loc_lower in lemma_lower:
                            countries.append(lemma_lower[loc_lower])
            except:
                # Разбиваем по запятым
                for loc in locations_data.split(','):
                    loc_lower = loc.strip().lower()
                    if loc_lower in lemma_lower:
                        countries.append(lemma_lower[loc_lower])
        else:
            # Простая строка с разделителями
            for loc in locations_data.split(','):
                loc_lower = loc.strip().lower()
                if loc_lower in lemma_lower:
                    countries.append(lemma_lower[loc_lower])

    # Обработка списков
    elif isinstance(locations_data, (list, tuple, set)):
        for loc in locations_data:
            loc_lower = str(loc).strip().lower()
            if loc_lower in lemma_lower:
                countries.append(lemma_lower[loc_lower])

    # Обработка других типов
    else:
        loc_lower = str(locations_data).strip().lower()
        if loc_lower in lemma_lower:
            countries.append(lemma_lower[loc_lower])

    return list(set(countries))

def safe_extract_countries(locations_str, lemma_to_country):
    try:
        return extract_countries_from_locations_simple(locations_str, lemma_to_country)
    except Exception as e:
        print(f"Критическая ошибка для {locations_str}: {e}")
        return []



