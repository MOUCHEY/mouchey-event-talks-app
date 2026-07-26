document.addEventListener('DOMContentLoaded', () => {
    // State
    let allUpdates = [];
    let activeFilter = 'all';
    let searchQuery = '';

    // DOM Elements
    const feedList = document.getElementById('feed-list');
    const loadingState = document.getElementById('loading-state');
    const emptyState = document.getElementById('empty-state');
    const errorBanner = document.getElementById('error-banner');
    const errorMessage = document.getElementById('error-message');
    const refreshBtn = document.getElementById('refresh-btn');
    const refreshIcon = document.getElementById('refresh-icon');
    const searchInput = document.getElementById('search-input');
    const filterContainer = document.getElementById('filter-container');

    // Tweet Modal Elements
    const tweetModal = document.getElementById('tweet-modal');
    const tweetTextarea = document.getElementById('tweet-textarea');
    const tweetCharCount = document.getElementById('tweet-char-count');
    const tweetCharCountContainer = document.getElementById('tweet-char-count').parentElement;
    const confirmTweetBtn = document.getElementById('confirm-tweet-btn');
    const cancelTweetBtn = document.getElementById('cancel-tweet-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalOverlay = document.getElementById('modal-overlay');

    // Fetch Release Notes
    async function fetchReleaseNotes() {
        showLoading(true);
        showError(false);
        refreshIcon.classList.add('spinning');
        refreshBtn.disabled = true;

        try {
            const response = await fetch('/api/releases');
            const data = await response.json();

            if (data.status === 'success') {
                processAndStoreReleases(data.releases);
                renderFeed();
            } else {
                throw new Error(data.message || 'Unknown backend error');
            }
        } catch (err) {
            console.error('Fetch error:', err);
            errorMessage.textContent = `Failed to fetch release notes: ${err.message}`;
            showError(true);
        } finally {
            showLoading(false);
            refreshIcon.classList.remove('spinning');
            refreshBtn.disabled = false;
        }
    }

    // Process Atom entries into individual update items
    function processAndStoreReleases(releases) {
        allUpdates = [];

        releases.forEach(release => {
            const date = release.date;
            const link = release.link;
            const contentHtml = release.content;

            // Parse HTML to separate sections
            const parser = new DOMParser();
            const doc = parser.parseFromString(contentHtml, 'text/html');
            
            let currentCategory = 'General';
            let currentElements = [];

            // Group sibling elements by preceding H3
            Array.from(doc.body.children).forEach(child => {
                if (child.tagName === 'H3') {
                    // Save previous category items if any
                    if (currentElements.length > 0) {
                        allUpdates.push({
                            date,
                            link,
                            category: currentCategory,
                            htmlContent: currentElements.join(''),
                            textContent: getStripedText(currentElements.join(''))
                        });
                    }
                    currentCategory = child.textContent.trim();
                    currentElements = [];
                } else {
                    currentElements.push(child.outerHTML);
                }
            });

            // Handle trailing section
            if (currentElements.length > 0) {
                allUpdates.push({
                    date,
                    link,
                    category: currentCategory,
                    htmlContent: currentElements.join(''),
                    textContent: getStripedText(currentElements.join(''))
                });
            }
        });
    }

    // Helper to strip HTML tags for plain text summary / tweeting
    function getStripedText(html) {
        const temp = document.createElement('div');
        temp.innerHTML = html;
        return temp.textContent || temp.innerText || "";
    }

    // Render Feed
    function renderFeed() {
        feedList.innerHTML = '';
        
        // Filter and Search
        const filtered = allUpdates.filter(update => {
            const matchesFilter = activeFilter === 'all' || 
                update.category.toLowerCase() === activeFilter.toLowerCase();
            
            const matchesSearch = searchQuery === '' || 
                update.date.toLowerCase().includes(searchQuery) ||
                update.category.toLowerCase().includes(searchQuery) ||
                update.textContent.toLowerCase().includes(searchQuery);

            return matchesFilter && matchesSearch;
        });

        if (filtered.length === 0) {
            emptyState.classList.remove('hidden');
            return;
        }
        emptyState.classList.add('hidden');

        // Group filtered updates by Date
        const grouped = {};
        filtered.forEach(update => {
            if (!grouped[update.date]) {
                grouped[update.date] = [];
            }
            grouped[update.date].push(update);
        });

        // Generate DOM for each date section
        Object.keys(grouped).forEach(date => {
            const dateSection = document.createElement('div');
            dateSection.className = 'date-section';

            const dateHeader = document.createElement('div');
            dateHeader.className = 'date-header';
            dateHeader.innerHTML = `
                <h3 class="date-title">${date}</h3>
                <div class="date-divider"></div>
            `;
            dateSection.appendChild(dateHeader);

            const cardsList = document.createElement('div');
            cardsList.className = 'cards-list';

            grouped[date].forEach(update => {
                const card = document.createElement('div');
                const catClass = update.category.toLowerCase();
                card.className = `update-card ${catClass}`;

                card.innerHTML = `
                    <div class="update-header">
                        <span class="badge ${catClass}">${update.category}</span>
                        <button class="share-action-btn" title="Tweet this update">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                            </svg>
                            <span>Tweet</span>
                        </button>
                    </div>
                    <div class="update-body">
                        ${update.htmlContent}
                    </div>
                `;

                // Add Share Button event listener
                card.querySelector('.share-action-btn').addEventListener('click', () => {
                    openTweetComposer(update);
                });

                cardsList.appendChild(card);
            });

            dateSection.appendChild(cardsList);
            feedList.appendChild(dateSection);
        });
    }

    // Modal & Tweeting Logic
    function openTweetComposer(update) {
        // Construct standard tweet draft
        const dateStr = update.date;
        const catStr = update.category.toUpperCase();
        let bodyText = update.textContent.trim();
        
        // Clean up redundant newlines or whitespace
        bodyText = bodyText.replace(/\s+/g, ' ');
        
        // Truncate text nicely to fit limits
        const intro = `BigQuery ${catStr} (${dateStr}): `;
        const hashtags = `\n#GoogleCloud #BigQuery`;
        const link = update.link ? `\n${update.link}` : '';
        
        const availableLength = 280 - intro.length - hashtags.length - link.length - 5;
        if (bodyText.length > availableLength) {
            bodyText = bodyText.substring(0, availableLength - 3) + '...';
        }

        tweetTextarea.value = `${intro}"${bodyText}"${link}${hashtags}`;
        updateCharCount();
        
        tweetModal.classList.remove('hidden');
        tweetTextarea.focus();
    }

    function closeTweetComposer() {
        tweetModal.classList.add('hidden');
    }

    function updateCharCount() {
        const len = tweetTextarea.value.length;
        tweetCharCount.textContent = len;
        
        if (len > 280) {
            tweetCharCountContainer.className = 'tweet-char-count-container danger';
            confirmTweetBtn.disabled = true;
        } else if (len > 250) {
            tweetCharCountContainer.className = 'tweet-char-count-container warning';
            confirmTweetBtn.disabled = false;
        } else {
            tweetCharCountContainer.className = 'tweet-char-count-container';
            confirmTweetBtn.disabled = false;
        }
    }

    function postTweet() {
        const text = encodeURIComponent(tweetTextarea.value);
        const twitterUrl = `https://twitter.com/intent/tweet?text=${text}`;
        window.open(twitterUrl, '_blank');
        closeTweetComposer();
    }

    // UI State Helpers
    function showLoading(show) {
        if (show) {
            loadingState.classList.remove('hidden');
            feedList.classList.add('hidden');
        } else {
            loadingState.classList.add('hidden');
            feedList.classList.remove('hidden');
        }
    }

    function showError(show) {
        if (show) {
            errorBanner.classList.remove('hidden');
        } else {
            errorBanner.classList.add('hidden');
        }
    }

    // Event Listeners
    refreshBtn.addEventListener('click', fetchReleaseNotes);
    
    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase().trim();
        renderFeed();
    });

    filterContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('chip')) {
            // Remove active from all siblings
            filterContainer.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            // Add to current
            e.target.classList.add('active');
            activeFilter = e.target.dataset.filter;
            renderFeed();
        }
    });

    // Modal Events
    closeModalBtn.addEventListener('click', closeTweetComposer);
    cancelTweetBtn.addEventListener('click', closeTweetComposer);
    modalOverlay.addEventListener('click', closeTweetComposer);
    tweetTextarea.addEventListener('input', updateCharCount);
    confirmTweetBtn.addEventListener('click', postTweet);

    // Initial Load
    fetchReleaseNotes();
});
