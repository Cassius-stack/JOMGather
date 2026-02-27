"""
Script to inject responsive CSS into community.html
"""
import re

RESPONSIVE_CSS = """
    /* ── Responsive / Mobile Layout ──────────────────── */
    @media (max-width: 768px) {
        .community-wrapper {
            height: calc(100vh - 80px);
            border-radius: 0;
            flex-direction: column;
            overflow-y: auto;
        }

        .community-wrapper > nav.sidebar {
            display: none;
        }

        .community-list-pane,
        .channel-list-pane {
            width: 100%;
            border-right: none;
            max-height: 200px;
            overflow-y: auto;
            flex-shrink: 0;
        }

        .channel-list-pane {
            border-bottom: 2px solid #e0e0e0;
        }

        #community-app {
            flex-direction: column !important;
            overflow-y: auto;
        }

        .community-modal {
            width: 95vw !important;
            max-width: 95vw;
        }

        .community-message {
            max-width: 92%;
        }

        .community-list-header h1 {
            font-size: 18px;
        }
    }

    @media (max-width: 480px) {
        .community-chat-header {
            padding: 10px 12px;
            flex-wrap: wrap;
            gap: 8px;
        }

        .community-messages {
            padding: 10px;
            gap: 8px;
        }

        .community-input-area {
            padding: 10px 12px;
            gap: 6px;
        }

        .community-message .msg-bubble {
            font-size: 13px;
        }
    }
"""

path = r"c:\Users\deong\OneDrive\Desktop\WDP\Project\JOMGather\templates\social\community.html"

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

MARKER = ".upp-btn-view:hover {"

if "Responsive / Mobile Layout" in content:
    print("Responsive CSS already present, skipping.")
else:
    # Find the last </style> before {% endblock %}
    idx = content.rfind("</style>")
    if idx == -1:
        print("ERROR: Could not find </style>")
    else:
        content = content[:idx] + RESPONSIVE_CSS + "\n" + content[idx:]
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Responsive CSS injected successfully.")
