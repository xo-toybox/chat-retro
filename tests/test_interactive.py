"""Tests for interactive components."""

import pytest

from chat_retro.interactive import (
    ANNOTATIONS_JS,
    DETAIL_VIEW_JS,
    FILTER_PANEL_JS,
    INTERACTIVE_CSS,
    SEARCH_JS,
    get_interactive_css,
    get_interactive_init_js,
    get_interactive_js,
)


class TestInteractiveCSS:
    """Test CSS generation."""

    def test_css_not_empty(self) -> None:
        css = get_interactive_css()
        assert len(css) > 0

    def test_contains_filter_styles(self) -> None:
        css = get_interactive_css()
        assert ".interactive-controls" in css
        assert ".control-group" in css

    def test_contains_search_styles(self) -> None:
        css = get_interactive_css()
        assert ".search-container" in css
        assert ".search-highlight" in css

    def test_contains_modal_styles(self) -> None:
        css = get_interactive_css()
        assert ".modal-overlay" in css
        assert ".modal-content" in css

    def test_contains_annotation_styles(self) -> None:
        css = get_interactive_css()
        assert ".annotation-container" in css
        assert ".saved-annotation" in css

    def test_contains_filter_badge_styles(self) -> None:
        css = get_interactive_css()
        assert ".filter-badge" in css
        assert ".active-filters" in css


class TestFilterPanelJS:
    """Test filter panel JavaScript."""

    def test_defines_filter_panel_class(self) -> None:
        assert "class FilterPanel" in FILTER_PANEL_JS

    def test_has_date_filter_inputs(self) -> None:
        assert "filter-date-start" in FILTER_PANEL_JS
        assert "filter-date-end" in FILTER_PANEL_JS

    def test_has_topic_filter(self) -> None:
        assert "filter-topic" in FILTER_PANEL_JS

    def test_has_sentiment_filter(self) -> None:
        assert "filter-sentiment" in FILTER_PANEL_JS
        assert "positive" in FILTER_PANEL_JS
        assert "negative" in FILTER_PANEL_JS

    def test_has_clear_button(self) -> None:
        assert "filter-clear" in FILTER_PANEL_JS
        assert "clearFilters" in FILTER_PANEL_JS

    def test_has_active_badges(self) -> None:
        assert "active-filters" in FILTER_PANEL_JS
        assert "updateActiveBadges" in FILTER_PANEL_JS


class TestSearchJS:
    """Test search JavaScript."""

    def test_defines_search_class(self) -> None:
        assert "class SearchComponent" in SEARCH_JS

    def test_has_search_input(self) -> None:
        assert "search-input" in SEARCH_JS

    def test_has_debounce(self) -> None:
        assert "debounceTimer" in SEARCH_JS
        assert "setTimeout" in SEARCH_JS

    def test_has_highlight_function(self) -> None:
        assert "highlightText" in SEARCH_JS
        assert "search-highlight" in SEARCH_JS

    def test_highlight_escapes_regex(self) -> None:
        # Should escape special regex characters
        assert "replace(/[.*+?^${}()" in SEARCH_JS


class TestDetailViewJS:
    """Test detail view JavaScript."""

    def test_defines_detail_view_class(self) -> None:
        assert "class DetailView" in DETAIL_VIEW_JS

    def test_creates_modal(self) -> None:
        assert "detail-modal" in DETAIL_VIEW_JS
        assert "modal-overlay" in DETAIL_VIEW_JS

    def test_has_show_and_close(self) -> None:
        assert "show(" in DETAIL_VIEW_JS
        assert "close()" in DETAIL_VIEW_JS

    def test_closes_on_escape(self) -> None:
        assert "Escape" in DETAIL_VIEW_JS

    def test_closes_on_backdrop_click(self) -> None:
        assert "e.target === modal" in DETAIL_VIEW_JS

    def test_has_format_pattern_helper(self) -> None:
        assert "formatPatternDetails" in DETAIL_VIEW_JS


class TestAnnotationsJS:
    """Test annotations JavaScript."""

    def test_defines_annotation_manager_class(self) -> None:
        assert "class AnnotationManager" in ANNOTATIONS_JS

    def test_uses_local_storage(self) -> None:
        assert "localStorage" in ANNOTATIONS_JS
        assert "getItem" in ANNOTATIONS_JS
        assert "setItem" in ANNOTATIONS_JS

    def test_has_crud_operations(self) -> None:
        assert "get(" in ANNOTATIONS_JS
        assert "set(" in ANNOTATIONS_JS
        assert "load(" in ANNOTATIONS_JS
        assert "save(" in ANNOTATIONS_JS

    def test_has_ui_methods(self) -> None:
        assert "createAnnotationUI" in ANNOTATIONS_JS
        assert "showForm" in ANNOTATIONS_JS
        assert "hideForm" in ANNOTATIONS_JS

    def test_has_save_and_delete(self) -> None:
        assert "saveAnnotation" in ANNOTATIONS_JS
        assert "deleteAnnotation" in ANNOTATIONS_JS

    def test_stores_timestamp(self) -> None:
        assert "timestamp" in ANNOTATIONS_JS
        assert "toISOString" in ANNOTATIONS_JS


class TestGetInteractiveJS:
    """Test get_interactive_js function."""

    def test_includes_all_by_default(self) -> None:
        js = get_interactive_js()
        assert "FilterPanel" in js
        assert "SearchComponent" in js
        assert "DetailView" in js
        assert "AnnotationManager" in js

    def test_excludes_filters_when_disabled(self) -> None:
        js = get_interactive_js(include_filters=False)
        assert "FilterPanel" not in js
        assert "SearchComponent" in js

    def test_excludes_search_when_disabled(self) -> None:
        js = get_interactive_js(include_search=False)
        assert "FilterPanel" in js
        assert "SearchComponent" not in js

    def test_excludes_details_when_disabled(self) -> None:
        js = get_interactive_js(include_details=False)
        assert "DetailView" not in js
        assert "AnnotationManager" in js

    def test_excludes_annotations_when_disabled(self) -> None:
        js = get_interactive_js(include_annotations=False)
        assert "DetailView" in js
        assert "AnnotationManager" not in js

    def test_can_exclude_all(self) -> None:
        js = get_interactive_js(
            include_filters=False,
            include_search=False,
            include_details=False,
            include_annotations=False,
        )
        assert js == ""


class TestGetInteractiveInitJS:
    """Test initialization code."""

    def test_returns_init_code(self) -> None:
        init = get_interactive_init_js()
        assert len(init) > 0

    def test_initializes_annotation_manager(self) -> None:
        init = get_interactive_init_js(include_annotations=True)
        assert "annotationManager" in init
        assert "AnnotationManager" in init

    def test_excludes_annotations_when_disabled(self) -> None:
        init = get_interactive_init_js(include_annotations=False)
        assert "AnnotationManager" not in init

    def test_initializes_detail_view(self) -> None:
        init = get_interactive_init_js(include_details=True)
        assert "detailView" in init
        assert "DetailView" in init

    def test_excludes_details_when_disabled(self) -> None:
        init = get_interactive_init_js(include_details=False)
        assert "DetailView" not in init

    def test_uses_dom_content_loaded(self) -> None:
        init = get_interactive_init_js()
        assert "DOMContentLoaded" in init


class TestArtifactIntegration:
    """Test integration with ArtifactGenerator."""

    def test_generate_html_with_interactive(self) -> None:
        from chat_retro.artifacts import ArtifactGenerator

        gen = ArtifactGenerator()
        html = gen.generate_html(
            title="Test",
            data={"patterns": []},
            interactive=True,
        )

        # Should include interactive CSS
        assert ".interactive-controls" in html
        assert ".modal-overlay" in html

        # Should include interactive JS
        assert "FilterPanel" in html
        assert "SearchComponent" in html
        assert "DetailView" in html
        assert "AnnotationManager" in html

        # Should include controls container
        assert 'id="controls"' in html

    def test_generate_html_without_interactive(self) -> None:
        from chat_retro.artifacts import ArtifactGenerator

        gen = ArtifactGenerator()
        html = gen.generate_html(
            title="Test",
            data={"patterns": []},
            interactive=False,
        )

        # Should not include interactive components
        assert "FilterPanel" not in html
        assert ".interactive-controls" not in html
        assert 'id="controls"' not in html

    def test_generate_html_selective_interactive(self) -> None:
        from chat_retro.artifacts import ArtifactGenerator

        gen = ArtifactGenerator()
        html = gen.generate_html(
            title="Test",
            data={},
            interactive=True,
            include_filters=True,
            include_search=False,
            include_details=True,
            include_annotations=False,
        )

        assert "FilterPanel" in html
        assert "SearchComponent" not in html
        assert "DetailView" in html
        assert "AnnotationManager" not in html

    def test_interactive_html_is_self_contained(self) -> None:
        from chat_retro.artifacts import ArtifactGenerator

        gen = ArtifactGenerator()
        html = gen.generate_html(
            title="Test",
            data={},
            interactive=True,
            include_d3=False,  # Skip D3 to avoid license URLs
        )

        # Should not have link/script tags referencing external URLs
        # (D3 library may contain http:// in comments/license, so we exclude it)
        assert '<link href="http' not in html
        assert '<script src="http' not in html
