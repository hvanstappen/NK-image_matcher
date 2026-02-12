// State management
const STORAGE_KEY = 'imageMatcherSelections';
let selections = loadSelections();
let currentItemIndex = 0;
let currentMatchIndex = 0;

// DOM Elements
const downloadBtn = document.getElementById('downloadBtn');
const clearSelectionsBtn = document.getElementById('clearSelectionsBtn');
const selectionCount = document.getElementById('selectionCount');
const itemsContainer = document.getElementById('itemsContainer');
const previewModal = document.getElementById('previewModal');
const previewImage = document.getElementById('previewImage');
const closePreviewBtn = document.getElementById('closePreview');
const toast = document.getElementById('toast');

// We verwijderen hier de referenties naar 'searchBox' omdat die in de HTML is vervangen door 'objInput'
// en die wordt afgehandeld door het script in de HTML zelf.

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    updateSelectionUI();
    restoreSelections();
    setupEventListeners();
});

// LocalStorage functions
function loadSelections() {
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    } catch (e) {
        console.error('Failed to load selections:', e);
        return [];
    }
}

function saveSelections() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(selections));
    } catch (e) {
        console.error('Failed to save selections:', e);
        showToast('Failed to save selections', 'error');
    }
}

function restoreSelections() {
    const matchCards = document.querySelectorAll('.match-card');
    matchCards.forEach(card => {
        const itemCard = card.closest('.item-card');
        if (!itemCard) return;

        const objNum = itemCard.dataset.objectNumber;
        const srcFile = itemCard.dataset.sourceFilename;
        const matchFile = card.dataset.filename;

        const isSelected = selections.some(s =>
        s.objectNumber === objNum &&
        s.sourceFile === srcFile &&
        s.matchFile === matchFile
        );

        if (isSelected) {
            card.classList.add('selected');
        }
    });
}

// Selection functions
function toggleSelection(card) {
    const itemCard = card.closest('.item-card');
    if (!itemCard) return;

    const objNum = itemCard.dataset.objectNumber;
    const srcFile = itemCard.dataset.sourceFilename;
    const matchFile = card.dataset.filename;
    const matchBase = card.dataset.base;
    const similarity = parseFloat(card.dataset.similarity);

    const existingIndex = selections.findIndex(s =>
    s.objectNumber === objNum &&
    s.sourceFile === srcFile &&
    s.matchFile === matchFile
    );

    if (existingIndex >= 0) {
        selections.splice(existingIndex, 1);
        card.classList.remove('selected');
        showToast('Selection removed');
    } else {
        selections.push({
            objectNumber: objNum,
            sourceFile: srcFile,
            matchFile: matchFile,
            matchBase: matchBase,
            similarity: similarity
        });
        card.classList.add('selected');
        showToast('Selection added');
    }

    saveSelections();
    updateSelectionUI();
}

function updateSelectionUI() {
    if (selectionCount) {
        selectionCount.textContent = selections.length;
    }
}

function clearAllSelections() {
    if (selections.length === 0) {
        showToast('No selections to clear');
        return;
    }

    if (confirm(`Clear all ${selections.length} selections?`)) {
        selections = [];
        saveSelections();
        updateSelectionUI();
        document.querySelectorAll('.match-card.selected').forEach(card => {
            card.classList.remove('selected');
        });
        showToast('All selections cleared');
    }
}

function downloadSelections() {
    if (selections.length === 0) {
        showToast('No selections to download', 'error');
        return;
    }

    const header = 'object_number,source_image,match_image,match_id,similarity\n';
    const rows = selections.map(s =>
    `${s.objectNumber},${s.sourceFile},${s.matchFile},${s.matchBase},${s.similarity}`
    ).join('\n');

    const csv = header + rows;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `selected_matches_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();

    URL.revokeObjectURL(url);
    showToast(`Downloaded ${selections.length} selections`);
}

// Preview modal
function showPreview(src) {
    if (previewImage && previewModal) {
        previewImage.src = src;
        previewModal.classList.add('active');
    }
}

function hidePreview() {
    if (previewModal) {
        previewModal.classList.remove('active');
    }
}

// Toast notification
function showToast(message, type = 'success') {
    if (!toast) return;

    toast.textContent = message;
    toast.className = 'toast show';
    if (type === 'error') {
        toast.style.background = '#D32F2F';
    } else {
        toast.style.background = '#212121';
    }

    setTimeout(() => {
        toast.classList.remove('show');
    }, 2000);
}

// Keyboard navigation helpers
function getVisibleItems() {
    return Array.from(document.querySelectorAll('.item-card:not(.hidden)'));
}

function getMatchCards(itemCard) {
    return Array.from(itemCard.querySelectorAll('.match-card'));
}

function focusItem(index) {
    const items = getVisibleItems();
    if (items.length === 0) return;

    currentItemIndex = Math.max(0, Math.min(index, items.length - 1));

    items.forEach((item, i) => {
        item.classList.toggle('focused', i === currentItemIndex);
    });

    const currentItem = items[currentItemIndex];
    currentItem.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Reset match index and focus first match
    currentMatchIndex = 0;
    focusMatch(0);
}

function focusMatch(index) {
    const items = getVisibleItems();
    if (items.length === 0) return;

    const currentItem = items[currentItemIndex];
    const matches = getMatchCards(currentItem);
    if (matches.length === 0) return;

    currentMatchIndex = Math.max(0, Math.min(index, matches.length - 1));

    matches.forEach((match, i) => {
        if (i === currentMatchIndex) {
            match.focus();
            match.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        }
    });
}

function handleKeydown(e) {
    // Zoekbalk check (objInput bestaat nu alleen in HTML, niet hier als variabele,
    // dus checken we document.activeElement direct)
    if (document.activeElement.tagName === 'INPUT') return;

    // Escape closes modal
    if (e.key === 'Escape') {
        if (previewModal && previewModal.classList.contains('active')) {
            hidePreview();
        }
        return;
    }

    const items = getVisibleItems();
    if (items.length === 0) return;

    switch (e.key) {
        case 'ArrowDown':
            e.preventDefault();
            focusItem(currentItemIndex + 1);
            break;
        case 'ArrowUp':
            e.preventDefault();
            focusItem(currentItemIndex - 1);
            break;
        case 'ArrowRight':
            e.preventDefault();
            focusMatch(currentMatchIndex + 1);
            break;
        case 'ArrowLeft':
            e.preventDefault();
            focusMatch(currentMatchIndex - 1);
            break;
        case 'Enter':
        case ' ':
            e.preventDefault();
            const currentItem = items[currentItemIndex];
            const matches = getMatchCards(currentItem);
            if (matches[currentMatchIndex]) {
                toggleSelection(matches[currentMatchIndex]);
            }
            break;
    }
}

// Event listeners
function setupEventListeners() {
    // Knoppen (check eerst of ze bestaan om errors te voorkomen)
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadSelections);
    }
    if (clearSelectionsBtn) {
        clearSelectionsBtn.addEventListener('click', clearAllSelections);
    }

    // Match card clicks
    document.querySelectorAll('.match-card').forEach(card => {
        card.addEventListener('click', (e) => {
            // Don't toggle if clicking the link
            if (e.target.closest('.match-id')) return;
            toggleSelection(card);
        });
    });

    // Source image clicks for preview
    document.querySelectorAll('.source-img').forEach(img => {
        img.addEventListener('click', () => showPreview(img.src));
    });

    // Match image double-click for preview
    document.querySelectorAll('.match-card img').forEach(img => {
        img.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            showPreview(img.src);
        });
    });

    // Modal
    if (closePreviewBtn) {
        closePreviewBtn.addEventListener('click', hidePreview);
    }
    if (previewModal) {
        previewModal.addEventListener('click', (e) => {
            if (e.target === previewModal) hidePreview();
        });
    }

    // Keyboard navigation
    document.addEventListener('keydown', handleKeydown);
}

// Hover Preview logic
const preview = document.getElementById("hover-preview");

if (preview) {
    const previewImg = preview.querySelector("img");

    document.addEventListener("mousemove", (event) => {
        const hovered = event.target.closest(".match-card img, .source-section img");

        if (!hovered) {
            preview.style.display = "none";
            preview.style.opacity = 0;
            return;
        }

        if (previewImg) {
            previewImg.src = hovered.src;
        }

        // Get bounding box of the hovered image
        const rect = hovered.getBoundingClientRect();

        // Desired default position: right side of the thumbnail
        let top = rect.top;
        let left = rect.right + 15;

        // Clamp inside viewport (avoid going off-screen)
        const maxWidth = 500;
        const maxHeight = 500;

        // If preview would go off the right edge → flip to the left
        if (left + maxWidth + 20 > window.innerWidth) {
            left = rect.left - maxWidth - 15;
        }

        // If preview would go off the bottom → lift it
        if (top + maxHeight + 20 > window.innerHeight) {
            top = window.innerHeight - maxHeight - 20;
        }

        // Apply position
        preview.style.left = left + "px";
        preview.style.top = top + "px";

        // Show preview
        preview.style.display = "block";

        // Allow fade-in
        requestAnimationFrame(() => {
            preview.style.opacity = 1;
        });
    });
}
