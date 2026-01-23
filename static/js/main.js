/* JOMGather Custom JavaScript */

// Document ready
document.addEventListener('DOMContentLoaded', function () {
    console.log('JOMGather loaded successfully!');

    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
});

// Main Search Logic
document.addEventListener('DOMContentLoaded', () => {
    // Dashboard Search Logic
    const searchInput = document.getElementById('dashboardSearchInput');
    const searchDropdown = document.getElementById('searchDropdown');
    const searchResults = document.getElementById('searchResultsContent');
    const tabPeople = document.getElementById('tabPeople');
    const tabActivities = document.getElementById('tabActivities');

    let currentTab = 'people';
    let cachedUsers = []; // Store fetched users to re-render on tab switch
    let debounceTimer;

    if (searchInput && searchDropdown) {
        // Input Listener
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();
            currentQuery = query;

            if (query.length < 2) {
                searchDropdown.classList.add('d-none');
                return;
            }

            searchDropdown.classList.remove('d-none');

            debounceTimer = setTimeout(() => {
                fetchResults(query);
            }, 300);
        });

        // Enter Key Listener (Redirect to Results Page)
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = searchInput.value.trim();
                if (query.length > 0) {
                    window.location.href = `/social/search-results?q=${encodeURIComponent(query)}`;
                }
            }
        });

        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
                searchDropdown.classList.add('d-none');
            }
        });

        // Show dropdown again if focused and has query
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim().length >= 2) {
                searchDropdown.classList.remove('d-none');
            }
        });
    }

    // Tab Logic
    if (tabPeople && tabActivities) {
        tabPeople.addEventListener('click', () => {
            switchTab('people');
        });
        tabActivities.addEventListener('click', () => {
            switchTab('activities');
        });
    }

    function switchTab(tab) {
        currentTab = tab;
        // Update UI
        if (tab === 'people') {
            tabPeople.classList.add('text-primary', 'active-tab');
            tabPeople.classList.remove('text-muted');
            tabActivities.classList.remove('text-primary', 'active-tab');
            tabActivities.classList.add('text-muted');
        } else {
            tabActivities.classList.add('text-primary', 'active-tab');
            tabActivities.classList.remove('text-muted');
            tabPeople.classList.remove('text-primary', 'active-tab');
            tabPeople.classList.add('text-muted');
        }
        renderResults();
    }

    async function fetchResults(query) {
        try {
            searchResults.innerHTML = '<div class="text-center text-muted py-3"><span class="spinner-border spinner-border-sm"></span> Searching...</div>';

            // Fetch Users (People)
            const res = await fetch(`/social/api/search?q=${encodeURIComponent(query)}`);
            cachedUsers = await res.json();

            renderResults();
        } catch (err) {
            console.error(err);
            searchResults.innerHTML = '<div class="text-center text-danger py-3">Error fetching results</div>';
        }
    }

    function renderResults() {
        searchResults.innerHTML = '';

        if (currentTab === 'people') {
            if (cachedUsers.length === 0) {
                searchResults.innerHTML = '<div class="text-center text-muted py-3">No people found.</div>';
                return;
            }
            // Render Users
            cachedUsers.forEach(user => createUserItem(user));
        } else {
            // Mock Activity Results
            searchResults.innerHTML = `
                <div class="list-group-item py-3 text-center">
                    <i class="bi bi-controller fs-3 text-warning mb-2"></i>
                    <h6 class="fw-bold">Activity Search</h6>
                    <p class="text-muted small mb-0">Feature coming soon! Try searching for "Chess" or "Cookie Baking".</p>
                </div>
            `;
        }
    }

    function createUserItem(user) {
        const item = document.createElement('div');
        item.className = 'd-flex align-items-center gap-3 p-3 border-bottom';
        item.style.cursor = 'default';

        let actionBtn = '';
        if (user.friendship_status === 'pending') {
            actionBtn = '<span class="badge bg-secondary rounded-pill">Requested</span>';
        } else if (user.friendship_status === 'accepted') {
            actionBtn = '<span class="badge bg-success rounded-pill">Friend</span>';
        } else if (user.friendship_status === 'received') {
            actionBtn = '<button class="btn btn-sm btn-primary rounded-pill btn-accept" data-id="' + user.id + '">Accept</button>';
        } else {
            actionBtn = '<button class="btn btn-sm btn-outline-primary rounded-pill btn-add" data-id="' + user.id + '"><i class="bi bi-person-plus"></i> Add</button>';
        }

        item.innerHTML = `
            <div style="width: 40px; height: 40px; background: #e0f2fe; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #1e3a5f;">
                <i class="bi bi-person-fill"></i>
            </div>
            <div class="flex-grow-1">
                <h6 class="mb-0 fw-bold" style="color: #1e3a5f;">${user.username}</h6>
                <small class="text-muted text-capitalize">${user.type}</small>
            </div>
            ${actionBtn}
        `;

        // Add Button Click
        const addBtn = item.querySelector('.btn-add');
        if (addBtn) {
            addBtn.addEventListener('click', (ev) => {
                ev.preventDefault();
                ev.stopPropagation(); // Prevent closing dropdown
                sendFriendRequest(user.id, addBtn);
            });
        }

        // Accept Button Click
        const acceptBtn = item.querySelector('.btn-accept');
        if (acceptBtn) {
            acceptBtn.addEventListener('click', (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                acceptFriendRequest(user.id, acceptBtn);
            });
        }

        searchResults.appendChild(item);
    }
});

async function sendFriendRequest(targetId, btn) {
    try {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        const res = await fetch('/social/api/friend-request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_id: targetId })
        });

        if (res.ok) {
            btn.className = 'badge bg-secondary rounded-pill';
            btn.innerHTML = 'Requested';
            btn.replaceWith(btn); // Remove listener
        } else {
            console.error('Request failed');
            btn.innerHTML = 'Error';
        }
    } catch (err) {
        console.error(err);
    }
}

async function acceptFriendRequest(requesterId, btn) {
    try {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        const res = await fetch('/social/api/friend-accept', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ requester_id: requesterId })
        });

        if (res.ok) {
            btn.className = 'badge bg-success rounded-pill';
            btn.innerHTML = 'Friend';
            btn.replaceWith(btn);
        }
    } catch (err) {
        console.error(err);
    }
}
