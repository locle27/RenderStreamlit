// Development toolbar functionality
class DevToolbar {
    constructor() {
        console.log('DevToolbar: Initializing...');
        this.selectedElement = null;
        this.comments = [];
        this.init();
    }

    init() {
        // Only initialize in development mode
        console.log('DevToolbar: Checking dev mode...');
        console.log('DevToolbar: data-dev-mode =', document.body.hasAttribute('data-dev-mode'));
        
        if (!document.body.hasAttribute('data-dev-mode')) {
            console.log('DevToolbar: Not in development mode, exiting.');
            return;
        }
        
        console.log('DevToolbar: Creating toolbar...');
        this.createToolbar();
        this.initElementSelection();
        this.loadComments();
        console.log('DevToolbar: Initialization complete.');
    }

    createToolbar() {
        const toolbar = document.createElement('div');
        toolbar.id = 'dev-toolbar';
        toolbar.innerHTML = `
            <div class="dev-toolbar-header">
                <h3>🛠️ Dev Toolbar</h3>
                <button id="dev-toolbar-toggle">▼</button>
            </div>
            <div class="dev-toolbar-content">
                <div class="dev-toolbar-section">
                    <h4>Selected Element</h4>
                    <div id="selected-element-info">No element selected</div>
                </div>
                <div class="dev-toolbar-section">
                    <h4>Add Comment</h4>
                    <textarea id="comment-input" placeholder="Enter your comment..."></textarea>
                    <button id="save-comment" class="btn btn-primary btn-sm">Save Comment</button>
                </div>
                <div class="dev-toolbar-section">
                    <h4>Comments</h4>
                    <div id="comments-list"></div>
                    <button id="export-comments" class="btn btn-secondary btn-sm">Export Comments</button>
                    <button id="reset-comments" class="btn btn-danger btn-sm" style="margin-left: 5px;">Reset History</button>
                </div>
            </div>
        `;
        document.body.appendChild(toolbar);

        // Add styles
        const styles = document.createElement('style');
        styles.textContent = `
            #dev-toolbar {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 300px;
                background: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 10000;
            }
            .dev-toolbar-header {
                padding: 10px;
                background: #f5f5f5;
                border-bottom: 1px solid #ccc;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .dev-toolbar-content {
                padding: 10px;
                max-height: 500px;
                overflow-y: auto;
            }
            .dev-toolbar-section {
                margin-bottom: 15px;
            }
            #comment-input {
                width: 100%;
                min-height: 60px;
                margin: 5px 0;
            }
            .selected-element {
                outline: 2px solid #ff4b4b !important;
            }
            .hovering-element {
                outline: 2px dashed #ff4b4b !important;
            }
        `;
        document.head.appendChild(styles);

        // Add event listeners
        document.getElementById('dev-toolbar-toggle').addEventListener('click', () => {
            const content = toolbar.querySelector('.dev-toolbar-content');
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
        });

        document.getElementById('save-comment').addEventListener('click', () => this.saveComment());
        document.getElementById('export-comments').addEventListener('click', () => this.exportComments());
        document.getElementById('reset-comments').addEventListener('click', () => this.resetComments());
    }

    initElementSelection() {
        let hoveredElement = null;

        document.addEventListener('mouseover', (e) => {
            if (e.target === this.selectedElement || e.target.closest('#dev-toolbar')) return;
            
            if (hoveredElement) {
                hoveredElement.classList.remove('hovering-element');
            }
            hoveredElement = e.target;
            hoveredElement.classList.add('hovering-element');
        });

        document.addEventListener('mouseout', (e) => {
            if (hoveredElement) {
                hoveredElement.classList.remove('hovering-element');
                hoveredElement = null;
            }
        });

        document.addEventListener('click', (e) => {
            if (e.target.closest('#dev-toolbar')) return;
            e.preventDefault();
            e.stopPropagation();

            if (this.selectedElement) {
                this.selectedElement.classList.remove('selected-element');
            }

            this.selectedElement = e.target;
            this.selectedElement.classList.add('selected-element');

            this.updateSelectedElementInfo();
        });
    }

    updateSelectedElementInfo() {
        if (!this.selectedElement) return;

        const info = {
            tag: this.selectedElement.tagName.toLowerCase(),
            id: this.selectedElement.id,
            classes: Array.from(this.selectedElement.classList).join(' '),
            text: this.selectedElement.textContent.trim().substring(0, 50) + '...'
        };

        document.getElementById('selected-element-info').innerHTML = `
            <div>Tag: ${info.tag}</div>
            ${info.id ? `<div>ID: ${info.id}</div>` : ''}
            ${info.classes ? `<div>Classes: ${info.classes}</div>` : ''}
            <div>Text: ${info.text}</div>
        `;
    }

    saveComment() {
        const commentInput = document.getElementById('comment-input');
        if (!this.selectedElement || !commentInput.value) return;

        const comment = {
            element: {
                tag: this.selectedElement.tagName.toLowerCase(),
                id: this.selectedElement.id,
                classes: Array.from(this.selectedElement.classList).join(' '),
                text: this.selectedElement.textContent.trim().substring(0, 50) + '...'
            },
            comment: commentInput.value,
            timestamp: new Date().toISOString()
        };

        this.comments.push(comment);
        this.saveComments();
        this.updateCommentsList();
        commentInput.value = '';
    }

    loadComments() {
        const saved = localStorage.getItem('devToolbarComments');
        if (saved) {
            this.comments = JSON.parse(saved);
            this.updateCommentsList();
        }
    }

    saveComments() {
        localStorage.setItem('devToolbarComments', JSON.stringify(this.comments));
    }

    updateCommentsList() {
        const list = document.getElementById('comments-list');
        list.innerHTML = this.comments.map((comment, index) => `
            <div class="comment" style="margin-bottom: 10px; padding: 5px; border: 1px solid #eee;">
                <div><strong>Element:</strong> ${comment.element.tag}${comment.element.id ? '#' + comment.element.id : ''}</div>
                <div><strong>Comment:</strong> ${comment.comment}</div>
                <div><small>${new Date(comment.timestamp).toLocaleString()}</small></div>
            </div>
        `).join('');
    }

    resetComments() {
        if (confirm('Are you sure you want to delete all comments? This cannot be undone.')) {
            this.comments = [];
            this.saveComments();
            this.updateCommentsList();
            
            // Remove the export UI if it's visible
            const exportContainer = document.getElementById('dev-toolbar-export-container');
            if (exportContainer) {
                exportContainer.remove();
            }
        }
    }

    exportComments() {
        if (this.comments.length === 0) {
            alert('There are no comments to export.');
            return;
        }

        const exportContainerId = 'dev-toolbar-export-container';
        let exportContainer = document.getElementById(exportContainerId);

        // Remove the container if it already exists to avoid duplicates
        if (exportContainer) {
            exportContainer.remove();
        }

        // Create a new container for the export UI
        exportContainer = document.createElement('div');
        exportContainer.id = exportContainerId;
        exportContainer.style.marginTop = '15px';

        // Create a textarea to display the JSON output
        const jsonOutput = document.createElement('textarea');
        jsonOutput.style.width = '100%';
        jsonOutput.style.minHeight = '150px';
        jsonOutput.value = JSON.stringify(this.comments, null, 2);
        jsonOutput.readOnly = true;

        // Create a button to copy the content to the clipboard
        const copyButton = document.createElement('button');
        copyButton.textContent = 'Copy to Clipboard';
        copyButton.className = 'btn btn-info btn-sm';
        copyButton.style.marginTop = '5px';

        copyButton.onclick = () => {
            jsonOutput.select();
            document.execCommand('copy');
            copyButton.textContent = 'Copied!';
            setTimeout(() => {
                copyButton.textContent = 'Copy to Clipboard';
            }, 2000);
        };

        // Append elements to the container and then to the toolbar
        exportContainer.appendChild(jsonOutput);
        exportContainer.appendChild(copyButton);
        document.getElementById('comments-list').parentElement.appendChild(exportContainer);
    }
}

// Initialize when the page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new DevToolbar());
} else {
    new DevToolbar();
} 