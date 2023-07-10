import pathlib
import re

from flask_babel import gettext as _
from kerko import extractors, transformers
from kerko.specs import FieldSpec
from whoosh.fields import STORED

from .transformers import extra_field_cleaner

# pylint: disable=invalid-name


class Config():

    def __init__(self):
        self.LIBSASS_INCLUDES = [
            str(pathlib.Path(__file__).parent.parent / 'static' / 'src' / 'vendor' / 'bootstrap' / 'scss'),
            str(pathlib.Path(__file__).parent.parent / 'static' / 'src' / 'vendor' / '@fortawesome' / 'fontawesome-free' / 'scss'),
        ]


class DevelopmentConfig(Config):

    def __init__(self):
        super().__init__()

        self.ASSETS_DEBUG = True  # Don't bundle/minify static assets.
        self.LIBSASS_STYLE = 'expanded'
        # self.EXPLAIN_TEMPLATE_LOADING = True


class ProductionConfig(Config):

    def __init__(self):
        super().__init__()

        self.ASSETS_DEBUG = False
        self.ASSETS_AUTO_BUILD = False
        self.LIBSASS_STYLE = 'compressed'


def update_composer(composer):
    """Update Kerko's `Composer` object."""

    # Replace the default 'data' extractor to strip unwanted data from the Extra field.
    composer.fields['data'].extractor = extractors.TransformerExtractor(
        extractor=extractors.RawDataExtractor(),
        transformers=[extra_field_cleaner]
    )

    # Add field for storing the formatted item preview used on search result
    # pages. This relies on the CSL style's in-text citation formatting and only
    # makes sense using our custom CSL style!
    composer.add_field(
        FieldSpec(
            key='preview',
            field_type=STORED,
            extractor=extractors.TransformerExtractor(
                extractor=extractors.ItemExtractor(key='citation', format_='citation'),
                # Zotero wraps the citation in a <span> element (most probably
                # because it expects the 'citation' format to be used in-text),
                # but that <span> has to be removed because our custom CSL style
                # causes <div>s to be nested within. Let's replace that <span>
                # with the same markup that the 'bib' format usually provides.
                transformers=[
                    lambda value: re.sub(r'^<span>', '<div class="csl-entry">', value, count=1),
                    lambda value: re.sub(r'</span>$', '</div>', value, count=1),
                ]
            )
        )
    )

    # Add extractors for the 'alternate_id' field.
    composer.fields['alternate_id'].extractor.extractors.append(
        extractors.TransformerExtractor(
            extractor=extractors.ItemDataExtractor(key='extra'),
            transformers=[
                transformers.find(
                    regex=r'^\s*EdTechHub.ItemAlsoKnownAs\s*:\s*(.*)$',
                    flags=re.IGNORECASE | re.MULTILINE,
                    max_matches=1,
                ),
                transformers.split(sep=';'),
            ]
        )
    )
    composer.fields['alternate_id'].extractor.extractors.append(
        extractors.TransformerExtractor(
            extractor=extractors.ItemDataExtractor(key='extra'),
            transformers=[
                transformers.find(
                    regex=r'^\s*KerkoCite.ItemAlsoKnownAs\s*:\s*(.*)$',
                    flags=re.IGNORECASE | re.MULTILINE,
                    max_matches=1,
                ),
                transformers.split(sep=' '),
            ]
        )
    )
    composer.fields['alternate_id'].extractor.extractors.append(
        extractors.TransformerExtractor(
            extractor=extractors.ItemDataExtractor(key='extra'),
            transformers=[
                transformers.find(
                    regex=r'^\s*shortDOI\s*:\s*(\S+)\s*$',
                    flags=re.IGNORECASE | re.MULTILINE,
                    max_matches=0,
                ),
            ]
        )
    )
