import pathlib
import re

from environs import Env
from flask_babel import gettext as _
from kerko import extractors, transformers
from kerko.composer import Composer
from kerko.specs import CollectionFacetSpec, FieldSpec
from whoosh.fields import STORED

from .transformers import extra_field_cleaner

# pylint: disable=invalid-name

env = Env()
env.read_env()


class Config():

    def __init__(self):
        app_dir = pathlib.Path(env.str('FLASK_APP')).parent.absolute()

        # Get configuration values from the environment.
        self.SECRET_KEY = env.str('SECRET_KEY')
        self.KERKO_ZOTERO_API_KEY = env.str('KERKO_ZOTERO_API_KEY')
        self.KERKO_ZOTERO_LIBRARY_ID = env.str('KERKO_ZOTERO_LIBRARY_ID')
        self.KERKO_ZOTERO_LIBRARY_TYPE = env.str('KERKO_ZOTERO_LIBRARY_TYPE')
        self.KERKO_DATA_DIR = env.str('KERKO_DATA_DIR', str(app_dir / 'data' / 'kerko'))

        # Set other configuration variables.
        self.LOGGING_HANDLER = 'default'

        self.LIBSASS_INCLUDES = [
            str(pathlib.Path(__file__).parent.parent / 'static' / 'src' / 'vendor' / 'bootstrap' / 'scss'),
            str(pathlib.Path(__file__).parent.parent / 'static' / 'src' / 'vendor' / '@fortawesome' / 'fontawesome-free' / 'scss'),
        ]

        self.BABEL_DEFAULT_LOCALE = 'en_GB'
        self.KERKO_WHOOSH_LANGUAGE = 'en'
        self.KERKO_ZOTERO_LOCALE = 'en-GB'

        self.HOME_URL = 'https://adaptdev.info'
        self.HOME_TITLE = _("Adaptive Management in International Development")
        # self.HOME_SUBTITLE = _("...")
        # self.ABOUT_URL = 'https://example.com'

        self.NAV_TITLE = _("Library")
        self.KERKO_TITLE = _("Library – Adaptive Management in International Development")
        self.KERKO_FULLTEXT_SEARCH = False
        self.KERKO_PRINT_ITEM_LINK = True
        self.KERKO_PRINT_CITATIONS_LINK = True
        self.KERKO_RESULTS_FIELDS = ['id', 'attachments', 'bib', 'coins', 'data', 'preview', 'url']
        self.KERKO_RESULTS_ABSTRACTS = True
        self.KERKO_RESULTS_ABSTRACTS_MAX_LENGTH = 500
        self.KERKO_RESULTS_ABSTRACTS_MAX_LENGTH_LEEWAY = 40
        self.KERKO_TEMPLATE_LAYOUT = 'app/layout.html.jinja2'
        self.KERKO_TEMPLATE_SEARCH = 'app/search.html.jinja2'
        self.KERKO_TEMPLATE_SEARCH_ITEM = 'app/search-item.html.jinja2'
        self.KERKO_TEMPLATE_ITEM = 'app/item.html.jinja2'
        self.KERKO_DOWNLOAD_ATTACHMENT_NEW_WINDOW = True
        self.KERKO_RELATIONS_INITIAL_LIMIT = 50
        self.KERKO_FEEDS = ['atom']
        self.KERKO_FEEDS_MAX_DAYS = 0

        # CAUTION: The URL's query string must be changed after any edit to the CSL
        # style, otherwise zotero.org might still use a previously cached version of
        # the file.
        self.KERKO_CSL_STYLE = 'https://docs.adaptdev.info/static/dist/csl/eth_apa.xml?202012301815'

        self.KERKO_COMPOSER = Composer(
            whoosh_language=self.KERKO_WHOOSH_LANGUAGE,
            exclude_default_facets=['facet_tag', 'facet_link'],
            exclude_default_fields=['data', 'text_docs'],  # No full-text search wanted on this lib.
            exclude_default_scopes=['metadata', 'fulltext'],  # No full-text search wanted on this lib.
            default_item_exclude_re=r'^_exclude$',
            default_child_include_re=r'^(_publish|publishPDF)$',
            default_child_exclude_re=r'',
            facet_initial_limit=6,
            facet_initial_limit_leeway=2,
        )

        # Replace the default 'data' extractor to strip unwanted data from the Extra field.
        self.KERKO_COMPOSER.add_field(
            FieldSpec(
                key='data',
                field_type=STORED,
                extractor=extractors.TransformerExtractor(
                    extractor=extractors.RawDataExtractor(),
                    transformers=[extra_field_cleaner]
                ),
            )
        )

        # Add field for storing the formatted item preview used on search result
        # pages. This relies on the CSL style's in-text citation formatting and only
        # makes sense using our custom CSL style!
        self.KERKO_COMPOSER.add_field(
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
        self.KERKO_COMPOSER.fields['alternate_id'].extractor.extractors.append(
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
        self.KERKO_COMPOSER.fields['alternate_id'].extractor.extractors.append(
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
        self.KERKO_COMPOSER.fields['alternate_id'].extractor.extractors.append(
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
        self.KERKO_COMPOSER.add_facet(
            CollectionFacetSpec(
                key='facet_theme',
                filter_key='theme',
                title=_('Theme'),
                weight=40,
                collection_key='Z7A9H37R',
                initial_limit=10,
                initial_limit_leeway=2,
            )
        )


class DevelopmentConfig(Config):

    def __init__(self):
        super().__init__()

        self.CONFIG = 'development'
        self.DEBUG = True
        self.ASSETS_DEBUG = env.bool('ASSETS_DEBUG', True)  # Don't bundle/minify static assets.
        self.LIBSASS_STYLE = 'expanded'
        self.LOGGING_LEVEL = env.str('LOGGING_LEVEL', 'DEBUG')
        # self.EXPLAIN_TEMPLATE_LOADING = True


class ProductionConfig(Config):

    def __init__(self):
        super().__init__()

        self.CONFIG = 'production'
        self.DEBUG = False
        self.ASSETS_DEBUG = env.bool('ASSETS_DEBUG', False)
        self.ASSETS_AUTO_BUILD = False
        self.LOGGING_LEVEL = env.str('LOGGING_LEVEL', 'WARNING')
        # TODO: self.GOOGLE_ANALYTICS_ID = 'UA-'
        self.LIBSASS_STYLE = 'compressed'


CONFIGS = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
