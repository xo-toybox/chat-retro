"""Interactive components for HTML artifacts.

Provides JavaScript/CSS templates for:
- Filter panel (date, topic, sentiment)
- Full-text search with highlighting
- Detail view modal
- Annotations with localStorage persistence
"""

# ============================================================================
# CSS for interactive components
# ============================================================================

INTERACTIVE_CSS = """\
/* Interactive Components */
.interactive-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.control-group label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.control-group input,
.control-group select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
}

.control-group input:focus,
.control-group select:focus {
  outline: none;
  border-color: #7c3aed;
  box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.1);
}

/* Search */
.search-container {
  flex: 1;
  min-width: 200px;
}

.search-container input {
  width: 100%;
}

.search-highlight {
  background: #fef3c7;
  padding: 0 2px;
  border-radius: 2px;
}

/* Filter badges */
.active-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.filter-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: #ede9fe;
  color: #5b21b6;
  border-radius: 9999px;
  font-size: 0.75rem;
}

.filter-badge button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  color: #7c3aed;
  font-weight: bold;
}

/* Detail modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s, visibility 0.2s;
}

.modal-overlay.active {
  opacity: 1;
  visibility: visible;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  transform: scale(0.95);
  transition: transform 0.2s;
}

.modal-overlay.active .modal-content {
  transform: scale(1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #eee;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
  line-height: 1;
}

.modal-close:hover {
  color: #333;
}

/* Expandable detail view */
.detail-expandable {
  cursor: pointer;
  transition: background 0.15s;
}

.detail-expandable:hover {
  background: #f5f3ff;
}

.detail-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease-out;
  background: #fafafa;
  border-radius: 0 0 8px 8px;
}

.detail-content.expanded {
  max-height: 500px;
  padding: 1rem;
}

/* Annotations */
.annotation-container {
  margin-top: 0.5rem;
}

.annotation-toggle {
  background: none;
  border: none;
  color: #7c3aed;
  font-size: 0.8rem;
  cursor: pointer;
  padding: 0.25rem 0;
}

.annotation-toggle:hover {
  text-decoration: underline;
}

.annotation-form {
  display: none;
  margin-top: 0.5rem;
}

.annotation-form.active {
  display: block;
}

.annotation-form textarea {
  width: 100%;
  min-height: 60px;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  font-size: 0.9rem;
  resize: vertical;
}

.annotation-form textarea:focus {
  outline: none;
  border-color: #7c3aed;
}

.annotation-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.annotation-actions button {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
}

.annotation-save {
  background: #7c3aed;
  color: white;
  border: none;
}

.annotation-cancel {
  background: white;
  border: 1px solid #ddd;
  color: #666;
}

.saved-annotation {
  background: #fef3c7;
  padding: 0.5rem;
  border-radius: 4px;
  margin-top: 0.5rem;
  font-size: 0.85rem;
  border-left: 3px solid #f59e0b;
}

/* No results message */
.no-results {
  text-align: center;
  padding: 2rem;
  color: #666;
  font-style: italic;
}
"""


# ============================================================================
# JavaScript for filter panel
# ============================================================================

FILTER_PANEL_JS = """\
// Filter Panel Component
class FilterPanel {
  constructor(containerId, onFilter) {
    this.container = document.getElementById(containerId);
    this.onFilter = onFilter;
    this.filters = {
      dateStart: null,
      dateEnd: null,
      topic: '',
      sentiment: ''
    };
    this.render();
  }

  render() {
    const html = `
      <div class="interactive-controls">
        <div class="control-group">
          <label>Date From</label>
          <input type="date" id="filter-date-start">
        </div>
        <div class="control-group">
          <label>Date To</label>
          <input type="date" id="filter-date-end">
        </div>
        <div class="control-group">
          <label>Topic</label>
          <select id="filter-topic">
            <option value="">All Topics</option>
          </select>
        </div>
        <div class="control-group">
          <label>Sentiment</label>
          <select id="filter-sentiment">
            <option value="">All</option>
            <option value="positive">Positive</option>
            <option value="neutral">Neutral</option>
            <option value="negative">Negative</option>
          </select>
        </div>
        <div class="control-group" style="justify-content: flex-end;">
          <button id="filter-clear" style="padding: 0.5rem 1rem; background: #f3f4f6; border: none; border-radius: 4px; cursor: pointer;">Clear</button>
        </div>
      </div>
      <div class="active-filters" id="active-filters"></div>
    `;
    this.container.innerHTML = html;
    this.attachListeners();
  }

  populateTopics(topics) {
    const select = document.getElementById('filter-topic');
    topics.forEach(topic => {
      const option = document.createElement('option');
      option.value = topic;
      option.textContent = topic;
      select.appendChild(option);
    });
  }

  attachListeners() {
    document.getElementById('filter-date-start').addEventListener('change', (e) => {
      this.filters.dateStart = e.target.value || null;
      this.applyFilters();
    });

    document.getElementById('filter-date-end').addEventListener('change', (e) => {
      this.filters.dateEnd = e.target.value || null;
      this.applyFilters();
    });

    document.getElementById('filter-topic').addEventListener('change', (e) => {
      this.filters.topic = e.target.value;
      this.applyFilters();
    });

    document.getElementById('filter-sentiment').addEventListener('change', (e) => {
      this.filters.sentiment = e.target.value;
      this.applyFilters();
    });

    document.getElementById('filter-clear').addEventListener('click', () => {
      this.clearFilters();
    });
  }

  applyFilters() {
    this.updateActiveBadges();
    this.onFilter(this.filters);
  }

  updateActiveBadges() {
    const container = document.getElementById('active-filters');
    const badges = [];

    if (this.filters.dateStart) {
      badges.push(`<span class="filter-badge">From: ${this.filters.dateStart} <button onclick="filterPanel.clearFilter('dateStart')">&times;</button></span>`);
    }
    if (this.filters.dateEnd) {
      badges.push(`<span class="filter-badge">To: ${this.filters.dateEnd} <button onclick="filterPanel.clearFilter('dateEnd')">&times;</button></span>`);
    }
    if (this.filters.topic) {
      badges.push(`<span class="filter-badge">Topic: ${this.filters.topic} <button onclick="filterPanel.clearFilter('topic')">&times;</button></span>`);
    }
    if (this.filters.sentiment) {
      badges.push(`<span class="filter-badge">Sentiment: ${this.filters.sentiment} <button onclick="filterPanel.clearFilter('sentiment')">&times;</button></span>`);
    }

    container.innerHTML = badges.join('');
  }

  clearFilter(key) {
    this.filters[key] = key.startsWith('date') ? null : '';
    const inputId = `filter-${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`;
    const input = document.getElementById(inputId);
    if (input) input.value = '';
    this.applyFilters();
  }

  clearFilters() {
    this.filters = { dateStart: null, dateEnd: null, topic: '', sentiment: '' };
    document.getElementById('filter-date-start').value = '';
    document.getElementById('filter-date-end').value = '';
    document.getElementById('filter-topic').value = '';
    document.getElementById('filter-sentiment').value = '';
    this.applyFilters();
  }
}
"""


# ============================================================================
# JavaScript for search
# ============================================================================

SEARCH_JS = """\
// Search Component
class SearchComponent {
  constructor(containerId, onSearch) {
    this.container = document.getElementById(containerId);
    this.onSearch = onSearch;
    this.searchTerm = '';
    this.debounceTimer = null;
    this.render();
  }

  render() {
    const html = `
      <div class="search-container">
        <input type="text" id="search-input" placeholder="Search patterns, topics, conversations...">
      </div>
    `;
    this.container.innerHTML = html;
    this.attachListeners();
  }

  attachListeners() {
    const input = document.getElementById('search-input');
    input.addEventListener('input', (e) => {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => {
        this.searchTerm = e.target.value.trim().toLowerCase();
        this.onSearch(this.searchTerm);
      }, 200);
    });
  }

  static highlightText(text, term) {
    if (!term) return text;
    const regex = new RegExp(`(${term.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')})`, 'gi');
    return text.replace(regex, '<span class="search-highlight">$1</span>');
  }

  clear() {
    document.getElementById('search-input').value = '';
    this.searchTerm = '';
    this.onSearch('');
  }
}
"""


# ============================================================================
# JavaScript for detail view
# ============================================================================

DETAIL_VIEW_JS = """\
// Detail View Component
class DetailView {
  constructor() {
    this.createModal();
  }

  createModal() {
    const modal = document.createElement('div');
    modal.id = 'detail-modal';
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h3 id="modal-title">Details</h3>
          <button class="modal-close" onclick="detailView.close()">&times;</button>
        </div>
        <div id="modal-body"></div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', (e) => {
      if (e.target === modal) this.close();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.close();
    });
  }

  show(title, content) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = content;
    document.getElementById('detail-modal').classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  close() {
    document.getElementById('detail-modal').classList.remove('active');
    document.body.style.overflow = '';
  }

  static formatPatternDetails(pattern) {
    let html = '';

    if (pattern.description) {
      html += `<p style="margin-bottom: 1rem;">${pattern.description}</p>`;
    }

    if (pattern.confidence !== undefined) {
      html += `<p><strong>Confidence:</strong> ${Math.round(pattern.confidence * 100)}%</p>`;
    }

    if (pattern.examples && pattern.examples.length > 0) {
      html += '<h4 style="margin: 1rem 0 0.5rem;">Examples</h4><ul>';
      pattern.examples.forEach(ex => {
        html += `<li style="margin-bottom: 0.5rem;">${ex}</li>`;
      });
      html += '</ul>';
    }

    if (pattern.conversation_ids && pattern.conversation_ids.length > 0) {
      html += `<p style="margin-top: 1rem; color: #666; font-size: 0.85rem;">
        Found in ${pattern.conversation_ids.length} conversation(s)
      </p>`;
    }

    return html;
  }
}
"""


# ============================================================================
# JavaScript for annotations
# ============================================================================

ANNOTATIONS_JS = """\
// Annotations Component with localStorage
class AnnotationManager {
  constructor(storageKey = 'chat-retro-annotations') {
    this.storageKey = storageKey;
    this.annotations = this.load();
  }

  load() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      return stored ? JSON.parse(stored) : {};
    } catch (e) {
      console.warn('Failed to load annotations:', e);
      return {};
    }
  }

  save() {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.annotations));
    } catch (e) {
      console.warn('Failed to save annotations:', e);
    }
  }

  get(id) {
    return this.annotations[id] || null;
  }

  set(id, note) {
    if (note && note.trim()) {
      this.annotations[id] = {
        note: note.trim(),
        timestamp: new Date().toISOString()
      };
    } else {
      delete this.annotations[id];
    }
    this.save();
  }

  createAnnotationUI(patternId, containerElement) {
    const existing = this.get(patternId);

    const html = `
      <div class="annotation-container" data-pattern-id="${patternId}">
        ${existing ? `
          <div class="saved-annotation">
            <strong>Note:</strong> ${existing.note}
            <button class="annotation-toggle" onclick="annotationManager.editAnnotation('${patternId}')">Edit</button>
          </div>
        ` : `
          <button class="annotation-toggle" onclick="annotationManager.showForm('${patternId}')">
            + Add note
          </button>
        `}
        <div class="annotation-form" id="annotation-form-${patternId}">
          <textarea id="annotation-text-${patternId}" placeholder="Add your notes...">${existing ? existing.note : ''}</textarea>
          <div class="annotation-actions">
            <button class="annotation-save" onclick="annotationManager.saveAnnotation('${patternId}')">Save</button>
            <button class="annotation-cancel" onclick="annotationManager.hideForm('${patternId}')">Cancel</button>
            ${existing ? `<button class="annotation-cancel" onclick="annotationManager.deleteAnnotation('${patternId}')" style="color: #dc2626;">Delete</button>` : ''}
          </div>
        </div>
      </div>
    `;

    containerElement.innerHTML = html;
  }

  showForm(patternId) {
    document.getElementById(`annotation-form-${patternId}`).classList.add('active');
    document.getElementById(`annotation-text-${patternId}`).focus();
  }

  hideForm(patternId) {
    document.getElementById(`annotation-form-${patternId}`).classList.remove('active');
  }

  editAnnotation(patternId) {
    this.showForm(patternId);
  }

  saveAnnotation(patternId) {
    const text = document.getElementById(`annotation-text-${patternId}`).value;
    this.set(patternId, text);

    // Refresh the UI
    const container = document.querySelector(`[data-pattern-id="${patternId}"]`).parentElement;
    this.createAnnotationUI(patternId, container);
  }

  deleteAnnotation(patternId) {
    this.set(patternId, null);
    const container = document.querySelector(`[data-pattern-id="${patternId}"]`).parentElement;
    this.createAnnotationUI(patternId, container);
  }
}
"""


# ============================================================================
# Combined interactive components
# ============================================================================


def get_interactive_css() -> str:
    """Get CSS for all interactive components."""
    return INTERACTIVE_CSS


def get_interactive_js(
    include_filters: bool = True,
    include_search: bool = True,
    include_details: bool = True,
    include_annotations: bool = True,
) -> str:
    """Get JavaScript for interactive components.

    Args:
        include_filters: Include filter panel
        include_search: Include search component
        include_details: Include detail view modal
        include_annotations: Include annotation support

    Returns:
        Combined JavaScript string
    """
    parts = []

    if include_filters:
        parts.append(FILTER_PANEL_JS)

    if include_search:
        parts.append(SEARCH_JS)

    if include_details:
        parts.append(DETAIL_VIEW_JS)

    if include_annotations:
        parts.append(ANNOTATIONS_JS)

    return "\n\n".join(parts)


def get_interactive_init_js(
    include_details: bool = True,
    include_annotations: bool = True,
) -> str:
    """Get initialization code for interactive components.

    Args:
        include_details: Include detail view initialization
        include_annotations: Include annotation manager initialization

    Returns:
        JavaScript initialization code
    """
    parts = [
        "// Initialize interactive components",
        "let filterPanel, searchComponent, detailView, annotationManager;",
        "",
        "document.addEventListener('DOMContentLoaded', function() {",
    ]

    if include_annotations:
        parts.append("  // Initialize annotation manager")
        parts.append("  if (typeof AnnotationManager !== 'undefined') {")
        parts.append("    annotationManager = new AnnotationManager();")
        parts.append("  }")

    if include_details:
        parts.append("  // Initialize detail view modal")
        parts.append("  if (typeof DetailView !== 'undefined') {")
        parts.append("    detailView = new DetailView();")
        parts.append("  }")

    parts.append("  // Filter and search are initialized by visualization code")
    parts.append("});")

    return "\n".join(parts)
