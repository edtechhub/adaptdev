import pathlib
import re

from environs import Env
from flask_babel import gettext as _
from kerko import codecs, extractors, transformers
from kerko.composer import Composer
from kerko.specs import CollectionFacetSpec, FieldSpec
from whoosh.fields import STORED

from .transformers import extra_field_cleaner

env = Env()  # pylint: disable=invalid-name
env.read_env()


class Config():
    app_dir = pathlib.Path(env.str('FLASK_APP')).parent.absolute()

    # Get configuration values from the environment.
    SECRET_KEY = env.str('SECRET_KEY')
    KERKO_ZOTERO_API_KEY = env.str('KERKO_ZOTERO_API_KEY')
    KERKO_ZOTERO_LIBRARY_ID = env.str('KERKO_ZOTERO_LIBRARY_ID')
    KERKO_ZOTERO_LIBRARY_TYPE = env.str('KERKO_ZOTERO_LIBRARY_TYPE')
    KERKO_DATA_DIR = env.str('KERKO_DATA_DIR', str(app_dir / 'data' / 'kerko'))

    # Set other configuration variables.
    LOGGING_HANDLER = 'default'
    EXPLAIN_TEMPLATE_LOADING = False

    LIBSASS_INCLUDES = [
        str(pathlib.Path(__file__).parent.parent / 'static' / 'src' / 'vendor' / 'bootstrap' / 'scss'),
        str(pathlib.Path(__file__).parent.parent / 'static' / 'src' / 'vendor' / '@fortawesome' / 'fontawesome-free' / 'scss'),
    ]

    BABEL_DEFAULT_LOCALE = 'en_GB'
    KERKO_WHOOSH_LANGUAGE = 'en'
    KERKO_ZOTERO_LOCALE = 'en-GB'

    HOME_URL = 'https://adaptdev.info'
    HOME_TITLE = _("Adaptive Management in International Development")
    # HOME_SUBTITLE = _("...")
    # ABOUT_URL = 'https://example.com'

    NAV_TITLE = _("Library")
    KERKO_TITLE = _("Library – Adaptive Management in International Development")

    KERKO_PRINT_ITEM_LINK = True
    KERKO_PRINT_CITATIONS_LINK = True
    KERKO_RESULTS_FIELDS = ['id', 'attachments', 'bib', 'coins', 'data', 'preview', 'url']
    KERKO_RESULTS_ABSTRACTS = True
    KERKO_RESULTS_ABSTRACTS_MAX_LENGTH = 500
    KERKO_RESULTS_ABSTRACTS_MAX_LENGTH_LEEWAY = 40
    KERKO_TEMPLATE_BASE = 'app/base.html.jinja2'
    KERKO_TEMPLATE_LAYOUT = 'app/layout.html.jinja2'
    KERKO_TEMPLATE_SEARCH = 'app/search.html.jinja2'
    KERKO_TEMPLATE_SEARCH_ITEM = 'app/search-item.html.jinja2'
    KERKO_TEMPLATE_ITEM = 'app/item.html.jinja2'
    KERKO_DOWNLOAD_ATTACHMENT_NEW_WINDOW = True
    KERKO_RELATIONS_INITIAL_LIMIT = 50

    # CAUTION: The URL's query string must be changed after any edit to the CSL
    # style, otherwise zotero.org might still use a previously cached version of
    # the file.
    KERKO_CSL_STYLE = 'https://docs.edtechhub.org/static/dist/csl/eth_apa.xml?202012301815'

    KERKO_COMPOSER = Composer(
        whoosh_language=KERKO_WHOOSH_LANGUAGE,
        exclude_default_facets=['facet_tag', 'facet_link'],
        exclude_default_fields=['data', 'text_docs'],
        exclude_default_scopes=['metadata', 'fulltext'],
        default_child_include_re='^(_publish|publishPDF)$',
        default_child_exclude_re='',
    )

    # Replace the default 'data' extractor to strip unwanted data from the Extra field.
    KERKO_COMPOSER.add_field(
        FieldSpec(
            key='data',
            field_type=STORED,
            extractor=extractors.TransformerExtractor(
                extractor=extractors.RawDataExtractor(),
                transformers=[extra_field_cleaner]
            ),
            codec=codecs.JSONFieldCodec()
        )
    )

    # Add field for storing the formatted item preview used on search result
    # pages. This relies on the CSL style's in-text citation formatting and only
    # makes sense using our custom CSL style!
    KERKO_COMPOSER.add_field(
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

    # Add extractors for the 'alternateId' field.
    KERKO_COMPOSER.fields['alternateId'].extractor.extractors.append(
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
    KERKO_COMPOSER.fields['alternateId'].extractor.extractors.append(
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
    KERKO_COMPOSER.fields['alternateId'].extractor.extractors.append(
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

    # Themes facet.
    KERKO_COMPOSER.add_facet(
        CollectionFacetSpec(
            key='facet_theme',
            filter_key='theme',
            title=_('Theme'),
            weight=40,
            collection_key='Z7A9H37R',
        )
    )


class DevelopmentConfig(Config):
    CONFIG = 'development'
    DEBUG = True
    ASSETS_DEBUG = env.bool('ASSETS_DEBUG', True)  # Don't bundle/minify static assets.
    KERKO_ZOTERO_START = env.int('KERKO_ZOTERO_START', 0)
    KERKO_ZOTERO_END = env.int('KERKO_ZOTERO_END', 0)
    LIBSASS_STYLE = 'expanded'
    LOGGING_LEVEL = env.str('LOGGING_LEVEL', 'DEBUG')


class ProductionConfig(Config):
    CONFIG = 'production'
    DEBUG = False
    ASSETS_DEBUG = env.bool('ASSETS_DEBUG', False)
    ASSETS_AUTO_BUILD = False
    LOGGING_LEVEL = env.str('LOGGING_LEVEL', 'WARNING')
    # TODO: GOOGLE_ANALYTICS_ID = 'UA-'
    LIBSASS_STYLE = 'compressed'


CONFIGS = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
