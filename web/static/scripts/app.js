const App = (() => {
    let state = {
        memes: [],
        emotions: [],
        searchQuery: '',
        isLoading: false,
        isUploading: false
    };

    const listeners = new Set();

    function subscribe(fn) {
        listeners.add(fn);
        return () => listeners.delete(fn);
    }

    function notify() {
        listeners.forEach(fn => fn(state));
    }

    function setState(updates) {
        state = { ...state, ...updates };
        notify();
    }

    const api = {
        async fetchEmotions() {
            try {
                const res = await fetch('/api/emotions');
                const emotions = await res.json();
                setState({ emotions });
            } catch (err) {
                console.error('加载情绪失败:', err);
            }
        },

        async fetchMemes() {
            setState({ isLoading: true });
            try {
                const res = await fetch('/api/memes');
                const memes = await res.json();
                setState({ memes, isLoading: false });
            } catch (err) {
                console.error('加载失败:', err);
                setState({ isLoading: false });
            }
        },

        async searchMemes(tag) {
            setState({ isLoading: true, searchQuery: tag });
            try {
                const res = await fetch(`/api/memes/search?q=${encodeURIComponent(tag)}`);
                const memes = await res.json();
                setState({ memes, isLoading: false });
            } catch (err) {
                console.error('搜索失败:', err);
                setState({ isLoading: false });
            }
        },

        async uploadMeme(formData) {
            setState({ isUploading: true });
            try {
                const res = await fetch('/api/memes', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error);
                await this.fetchMemes();
                return { success: true };
            } catch (err) {
                setState({ isUploading: false });
                return { success: false, error: err.message };
            }
        },

        async updateMeme(filename, data) {
            try {
                const res = await fetch(`/api/memes/${filename}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (!res.ok) {
                    const d = await res.json();
                    throw new Error(d.error);
                }
                await this.fetchMemes();
                return { success: true };
            } catch (err) {
                return { success: false, error: err.message };
            }
        },

        async deleteMeme(filename) {
            try {
                const res = await fetch(`/api/memes/${filename}`, { method: 'DELETE' });
                if (!res.ok) {
                    const d = await res.json();
                    throw new Error(d.error);
                }
                await this.fetchMemes();
                return { success: true };
            } catch (err) {
                return { success: false, error: err.message };
            }
        }
    };

    return { api, subscribe, getState: () => state };
})();

const UI = {
    els: {},

    init() {
        this.els = {
            uploadForm: document.getElementById('uploadForm'),
            fileInput: document.getElementById('fileInput'),
            fileLabel: document.getElementById('fileLabel'),
            fileName: document.getElementById('fileName'),
            uploadBtn: document.getElementById('uploadBtn'),
            message: document.getElementById('message'),
            searchInput: document.getElementById('searchInput'),
            memeGrid: document.getElementById('memeGrid'),
            editModal: document.getElementById('editModal'),
            editForm: document.getElementById('editForm'),
            tagsInput: document.getElementById('tagsInput'),
            emotionPicker: document.getElementById('emotionPicker')
        };
        this.bindEvents();
    },

    bindEvents() {
        const { uploadForm, fileInput, fileLabel, searchInput, editForm, tagsInput, emotionPicker } = this.els;

        fileInput.addEventListener('change', () => this.handleFileSelect());
        this.dragDrop(fileLabel);

        uploadForm.addEventListener('submit', (e) => this.handleUpload(e));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch();
        });
        editForm.addEventListener('submit', (e) => this.handleEdit(e));

        document.getElementById('searchBtn').addEventListener('click', () => this.handleSearch());
        document.getElementById('clearSearchBtn').addEventListener('click', () => {
            searchInput.value = '';
            App.api.fetchMemes();
        });
        document.getElementById('closeModalBtn').addEventListener('click', () => this.closeModal());
        document.getElementById('editModal').addEventListener('click', (e) => {
            if (e.target.id === 'editModal') this.closeModal();
        });
        
        emotionPicker.addEventListener('click', (e) => {
            const tag = e.target.closest('.emotion-tag');
            if (tag) {
                this.handleEmotionClick(tag.dataset.emotion);
                this.renderEmotions();
            }
        });
        
        const tagsToggle = document.getElementById('tagsToggle');
        tagsToggle.addEventListener('click', () => {
            emotionPicker.classList.toggle('expanded');
            tagsToggle.textContent = emotionPicker.classList.contains('expanded') ? '收起 ↑' : '更多 ↓';
        });
    },

    handleFileSelect() {
        const file = this.els.fileInput.files[0];
        if (file) {
            this.els.fileName.textContent = `已选择: ${file.name} (${this.formatSize(file.size)})`;
            this.els.fileLabel.classList.add('has-file');
        } else {
            this.els.fileName.textContent = '';
            this.els.fileLabel.classList.remove('has-file');
        }
    },

    dragDrop(el) {
        el.addEventListener('dragover', (e) => { e.preventDefault(); el.classList.add('dragover'); });
        el.addEventListener('dragleave', () => el.classList.remove('dragover'));
        el.addEventListener('drop', (e) => {
            e.preventDefault();
            el.classList.remove('dragover');
            if (e.dataTransfer.files[0]) {
                this.els.fileInput.files = e.dataTransfer.files;
                this.handleFileSelect();
            }
        });
    },

    formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },

    async handleUpload(e) {
        e.preventDefault();
        const { fileInput, uploadBtn, tagsInput } = this.els;
        const file = fileInput.files[0];
        const name = document.getElementById('nameInput').value.trim();
        const tags = tagsInput.value.trim();

        if (!file) return this.showMessage('请选择图片文件', 'error');

        const formData = new FormData();
        formData.append('file', file);
        formData.append('name', name);
        formData.append('tags', tags);

        uploadBtn.disabled = true;
        uploadBtn.textContent = '上传中...';

        const result = await App.api.uploadMeme(formData);

        if (result.success) {
            this.showMessage('上传成功！', 'success');
            this.els.uploadForm.reset();
            this.els.fileName.textContent = '';
            this.els.fileLabel.classList.remove('has-file');
            this.renderEmotions();
        } else {
            this.showMessage(result.error || '上传失败', 'error');
        }

        uploadBtn.disabled = false;
        uploadBtn.textContent = '上传表情';
    },

    handleSearch() {
        const tag = this.els.searchInput.value.trim();
        if (tag) {
            App.api.searchMemes(tag);
        } else {
            App.api.fetchMemes();
        }
    },

    openEditModal(filename, name, tags) {
        document.getElementById('editFilename').value = filename;
        document.getElementById('editName').value = name;
        document.getElementById('editTags').value = tags;
        this.els.editModal.classList.add('show');
    },

    closeModal() {
        this.els.editModal.classList.remove('show');
    },

    async handleEdit(e) {
        e.preventDefault();
        const filename = document.getElementById('editFilename').value;
        const name = document.getElementById('editName').value.trim();
        const tags = document.getElementById('editTags').value.trim().split(',').map(t => t.trim()).filter(Boolean);

        const result = await App.api.updateMeme(filename, { name, tags });

        if (result.success) {
            this.showMessage('更新成功！', 'success');
            this.closeModal();
        } else {
            this.showMessage(result.error || '更新失败', 'error');
        }
    },

    async handleDelete(filename) {
        if (!confirm('确定要删除这个表情吗？')) return;

        const result = await App.api.deleteMeme(filename);
        if (result.success) {
            this.showMessage('删除成功！', 'success');
        } else {
            this.showMessage(result.error || '删除失败', 'error');
        }
    },

    showMessage(text, type) {
        this.els.message.textContent = text;
        this.els.message.className = `message ${type}`;
        setTimeout(() => this.els.message.className = 'message', 3000);
    },

    render() {
        const { memes, isLoading, isUploading } = App.getState();
        const grid = this.els.memeGrid;

        if (isLoading) {
            grid.innerHTML = '<div class="empty-state"><p>加载中...</p></div>';
            return;
        }

        if (!memes.length) {
            grid.innerHTML = '<div class="empty-state"><p>还没有表情</p><small>上传一个开始使用吧</small></div>';
            return;
        }

        grid.innerHTML = memes.map(meme => `
            <div class="meme-card">
                <img src="${meme.url}" alt="${this.escape(meme.name)}" class="meme-image" 
                     onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect fill=%22%23f5f7fa%22 width=%22100%22 height=%22100%22/><text x=%2250%22 y=%2255%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2210%22>图片加载失败</text></svg>'">
                <div class="meme-info">
                    <div class="meme-name" title="${this.escape(meme.name)}">${this.escape(meme.name)}</div>
                    <div class="meme-tags">
                        ${meme.tags.map(tag => `<span class="tag">${this.escape(tag)}</span>`).join('')}
                    </div>
                    <div class="meme-actions">
                        <button class="btn btn-small btn-edit" data-action="edit" data-filename="${meme.filename}" data-name="${this.escape(meme.name)}" data-tags="${meme.tags.join(',')}">编辑</button>
                        <button class="btn btn-small btn-danger" data-action="delete" data-filename="${meme.filename}">删除</button>
                    </div>
                </div>
            </div>
        `).join('');

        grid.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', () => {
                const { action, filename, name, tags } = btn.dataset;
                if (action === 'edit') this.openEditModal(filename, name, tags);
                if (action === 'delete') this.handleDelete(filename);
            });
        });
    },

    escape(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    renderEmotions() {
        const { emotions } = App.getState();
        const picker = this.els.emotionPicker;
        const tagsInput = this.els.tagsInput;
        if (!picker) return;

        const currentTags = tagsInput.value.split(',').map(t => t.trim()).filter(t => t);

        picker.innerHTML = emotions.map(emotion => `
            <span class="emotion-tag ${currentTags.includes(emotion) ? 'selected' : ''}" 
                  data-emotion="${this.escape(emotion)}">
                ${this.escape(emotion)}
            </span>
        `).join('');
    },

    handleEmotionClick(emotion) {
        const tagsInput = this.els.tagsInput;
        const currentTags = tagsInput.value.split(',').map(t => t.trim()).filter(t => t);
        
        let newTags;
        if (currentTags.includes(emotion)) {
            newTags = currentTags.filter(t => t !== emotion);
        } else {
            newTags = [...currentTags, emotion];
        }
        
        tagsInput.value = newTags.join(', ');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    UI.init();
    UI.renderEmotions();

    App.subscribe(() => UI.render());
    App.subscribe(() => UI.renderEmotions());

    App.api.fetchEmotions();
    App.api.fetchMemes();
});
