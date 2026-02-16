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

    if (searchInput) {
        console.log('Search input found, attaching listeners');

        // Input Listener (Dropdown)
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();

            if (searchDropdown) {
                if (query.length < 2) {
                    searchDropdown.classList.add('d-none');
                    return;
                }
                searchDropdown.classList.remove('d-none');
            }

            debounceTimer = setTimeout(() => {
                fetchResults(query);
            }, 300);
        });

        // Enter Key Listener (Redirect to Results Page)
        searchInput.addEventListener('keydown', (e) => {
            console.log('Key pressed:', e.key);
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = searchInput.value.trim();
                console.log('Enter pressed with query:', query);

                if (query.length > 0) {
                    const targetUrl = `/social/search-results?q=${encodeURIComponent(query)}`;
                    console.log('Redirecting to:', targetUrl);
                    window.location.href = targetUrl;
                }
            }
        });

        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (searchDropdown && !searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
                searchDropdown.classList.add('d-none');
            }
        });

        // Show dropdown again if focused and has query
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim().length >= 2 && searchDropdown) {
                searchDropdown.classList.remove('d-none');
            }
        });
    } else {
        console.warn('Dashboard search input not found on this page.');
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

    // === MODAL SEARCH LOGIC ===
    const modalSearchInput = document.getElementById('userSearchInput');
    const modalSearchResults = document.getElementById('searchResults');
    let modalDebounceTimer;

    if (modalSearchInput && modalSearchResults) {
        modalSearchInput.addEventListener('input', (e) => {
            clearTimeout(modalDebounceTimer);
            const query = e.target.value.trim();

            if (query.length < 2) {
                modalSearchResults.innerHTML = '<div class="text-center text-muted py-3"><small class="fs-6">Type to search for people...</small></div>';
                return;
            }

            modalDebounceTimer = setTimeout(async () => {
                try {
                    modalSearchResults.innerHTML = '<div class="text-center py-3"><span class="spinner-border spinner-border-sm text-primary"></span></div>';

                    const res = await fetch(`/social/api/search?q=${encodeURIComponent(query)}`);
                    const users = await res.json();

                    modalSearchResults.innerHTML = '';
                    if (users.length === 0) {
                        modalSearchResults.innerHTML = '<div class="text-center text-muted py-3">No users found.</div>';
                        return;
                    }

                    users.forEach(user => {
                        const item = document.createElement('div');
                        item.className = 'list-group-item border-0 d-flex align-items-center gap-3 py-3 px-3';

                        let actionBtn = '';
                        if (user.friendship_status === 'pending') {
                            actionBtn = '<button class="btn btn-sm btn-secondary rounded-pill" disabled>Requested</button>';
                        } else if (user.friendship_status === 'accepted') {
                            actionBtn = '<button class="btn btn-sm btn-success rounded-pill" disabled><i class="bi bi-check"></i> Friend</button>';
                        } else if (user.friendship_status === 'received') {
                            actionBtn = '<button class="btn btn-sm btn-primary rounded-pill btn-accept-modal" data-id="' + user.id + '">Accept</button>';
                        } else {
                            actionBtn = '<button class="btn btn-sm btn-primary rounded-pill btn-add-modal" style="background: #1e3a5f; border: none;" data-id="' + user.id + '"><i class="bi bi-person-plus"></i> Add</button>';
                        }

                        item.innerHTML = `
                            <a href="/profile/view/${user.id}" class="text-decoration-none d-flex align-items-center gap-3 flex-grow-1">
                                <div style="width: 50px; height: 50px; background: #e0f2fe; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #1e3a5f; font-size: 1.2rem;">
                                    <i class="bi bi-person-fill"></i>
                                </div>
                                <div class="flex-grow-1">
                                    <h6 class="mb-0 fw-bold" style="color: #1e3a5f;">${user.username}</h6>
                                    <small class="text-muted text-capitalize">${user.type}</small>
                                </div>
                            </a>
                            ${actionBtn}
                        `;

                        // Bind Events
                        const addBtn = item.querySelector('.btn-add-modal');
                        if (addBtn) {
                            addBtn.addEventListener('click', () => sendFriendRequest(user.id, addBtn));
                        }
                        const acceptBtn = item.querySelector('.btn-accept-modal');
                        if (acceptBtn) {
                            acceptBtn.addEventListener('click', () => acceptFriendRequest(user.id, acceptBtn));
                        }

                        modalSearchResults.appendChild(item);
                    });

                } catch (err) {
                    console.error(err);
                    modalSearchResults.innerHTML = '<div class="text-center text-danger py-3">Error searching.</div>';
                }
            }, 300);
        });
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
            <a href="/profile/view/${user.id}" class="text-decoration-none d-flex align-items-center gap-3 flex-grow-1">
                <div style="width: 40px; height: 40px; background: #e0f2fe; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #1e3a5f;">
                    <i class="bi bi-person-fill"></i>
                </div>
                <div class="flex-grow-1">
                    <h6 class="mb-0 fw-bold" style="color: #1e3a5f;">${user.username}</h6>
                    <small class="text-muted text-capitalize">${user.type}</small>
                </div>
            </a>
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

/**
 * Handle friendship actions from the notification dropdown
 * @param {Event} event 
 * @param {string} action 'accept' or 'reject'
 * @param {string} message The notification message to parse user info
 * @param {HTMLElement} btn The button clicked
 */
async function handleFriendRequest(event, action, message, btn) {
    event.preventDefault();
    event.stopPropagation(); // Keep dropdown open

    // Parse username from message (e.g., "Jeremy sent you a friend request!")
    const username = message.split(' ')[0];
    const endpoint = action === 'accept' ? '/social/api/friend-accept' : '/social/api/friend-reject';

    try {
        // Disable both buttons in the group
        const container = btn.parentElement;
        const buttons = container.querySelectorAll('button');
        buttons.forEach(b => b.disabled = true);

        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        // Find requester_id. This is tricky since it's not in the notification message usually.
        // We'll search for the user by name first OR we could have included it in the notification.
        // For now, let's search via API.
        const searchRes = await fetch(`/social/api/search?q=${encodeURIComponent(username)}`);
        const searchData = await searchRes.json();
        const user = searchData.find(u => u.username === username);

        if (!user) {
            alert('Could not find user details');
            buttons.forEach(b => b.disabled = false);
            btn.innerHTML = action === 'accept' ? 'Accept' : 'Reject';
            return;
        }

        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ requester_id: user.id })
        });

        if (res.ok) {
            const item = btn.closest('.notification-item-container');
            if (action === 'accept') {
                container.innerHTML = `<span class="text-success small"><i class="bi bi-check-circle-fill"></i> Friend Request Accepted</span>`;
            } else {
                container.innerHTML = `<span class="text-muted small"><i class="bi bi-x-circle"></i> Request Ignored</span>`;
            }

            // Optional: Remove item after a delay
            setTimeout(() => {
                if (item) {
                    item.style.opacity = '0';
                    setTimeout(() => item.remove(), 300);
                }
            }, 2000);
        } else {
            alert(`Failed to ${action} request`);
            buttons.forEach(b => b.disabled = false);
            btn.innerHTML = action === 'accept' ? 'Accept' : 'Reject';
        }
    } catch (err) {
        console.error(err);
        alert('An error occurred');
    }
}
