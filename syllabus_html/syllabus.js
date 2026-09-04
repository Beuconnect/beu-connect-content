// ===== 🚀 PRELOAD ASAP (PREVENT FLICKER) =====
document.documentElement.classList.add('preload');


// ===== MAIN LOGIC =====
document.addEventListener('DOMContentLoaded', () => {

    const $ = (sel, parent = document) => parent.querySelector(sel);
    const $$ = (sel, parent = document) => parent.querySelectorAll(sel);

    // ===== HEADER FIX =====
    const header = $('.page-header');
    const subtitle = $('.page-subtitle');
    const titleEl = $('.page-title');

    if (header && subtitle && titleEl) {
        header.insertBefore(subtitle, titleEl);
        titleEl.textContent = titleEl.textContent.replace(/\s*Syllabus/i, '').trim();
    }

    // ===== HIDE ALL CONTENT =====
    const allTabs = $$('.tab-content');
    const allButtons = $$('.tab-btn');

    const closeAllTabs = () => {
        allTabs.forEach(el => el.style.display = 'none');
        allButtons.forEach(el => el.classList.remove('active'));
    };

    closeAllTabs();

    // ===== CREDIT TOGGLE =====
    const creditsToggle = $('#credits-toggle');
    const creditsTable = $('#credits-table-container');

    creditsToggle?.addEventListener('click', () => {
        creditsToggle.classList.toggle('active');
        creditsTable?.classList.toggle('expanded');
    });

    // ===== MODAL =====
    const modal = $('#elective-modal');
    const modalTitle = $('#modal-title');
    const modalOptions = $('#modal-options');
    const modalClose = $('#modal-close');

    const closeModal = () => modal?.classList.remove('active');

    modalClose?.addEventListener('click', closeModal);

    modal?.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    const openModal = (btn) => {
        try {
            const title = btn.dataset.modalTitle || 'Select Option';
            const options = JSON.parse(btn.dataset.modalOptions || '[]');

            modalTitle.textContent = title;
            modalOptions.innerHTML = '';

            options.forEach(opt => {
                const b = document.createElement('button');
                b.className = "modal-option-btn";
                b.textContent = opt.label;

                b.onclick = () => {
                    const target = document.getElementById(opt.target);
                    if (!target) return;

                    closeAllTabs();

                    btn.insertAdjacentElement('afterend', target);
                    target.style.display = 'block';
                    btn.classList.add('active');

                    closeModal();
                };

                modalOptions.appendChild(b);
            });

            modal.classList.add('active');

        } catch (err) {
            console.error("Modal JSON error:", err);
        }
    };

    // ===== TAB / SUBJECT TOGGLE =====
    $('#filter-controls')?.addEventListener('click', (e) => {
        const btn = e.target.closest('.tab-btn');
        if (!btn) return;

        if (btn.dataset.modalTrigger !== undefined) {
            openModal(btn);
            return;
        }

        const target = document.getElementById(btn.dataset.target);
        if (!target) return;

        if (target.style.display === 'block') {
            target.style.display = 'none';
            btn.classList.remove('active');
            return;
        }

        closeAllTabs();

        btn.insertAdjacentElement('afterend', target);
        target.style.display = 'block';
        btn.classList.add('active');
    });

    // ===== ADD ACTION BUTTONS =====
    const addActionButtons = () => {
        $$('.unit-topics > li, .lab-card li').forEach(li => {
            if (li.querySelector('ul, ol, .topic-actions-container')) return;

            li.insertAdjacentHTML('beforeend', `
                <div class="topic-actions-container">
                    <button class="ask-ai-topic-button">Ask AI</button>
                    <button class="search-youtube-button">YouTube</button>
                    <button class="mark-complete-button">
                        <span class="mark-complete-text">Mark as Done</span>
                    </button>
                </div>
            `);
        });
    };

    requestAnimationFrame(addActionButtons);

    // ===== GO TO TOP =====
    const goTop = document.createElement('button');
    goTop.id = "goToTopBtn";
    goTop.innerText = "↑";

    document.body.appendChild(goTop);

    const toggleTopBtn = () => {
        const show = window.scrollY > 100;
        goTop.style.opacity = show ? "1" : "0";
        goTop.style.pointerEvents = show ? "auto" : "none";
    };

    window.addEventListener('scroll', toggleTopBtn, { passive: true });

    goTop.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    toggleTopBtn(); // fix initial state


    // ===== 🚀 SHOW UI AFTER EVERYTHING READY =====
    requestAnimationFrame(() => {
        document.documentElement.classList.remove('preload');
        document.documentElement.classList.add('loaded');
    });
});


// ===== GLOBAL CLICK HANDLER =====
document.addEventListener('click', (e) => {

    const li = e.target.closest('li');
    if (!li) return;

    // MARK COMPLETE
    if (e.target.closest('.mark-complete-button')) {
        li.classList.toggle('topic-completed');

        const text = li.querySelector('.mark-complete-text');
        if (text) {
            text.textContent = li.classList.contains('topic-completed')
                ? 'Done'
                : 'Mark as Done';
        }
        return;
    }

    // GET CLEAN TEXT
    const getTopicText = () => {
        const clone = li.cloneNode(true);
        clone.querySelector('.topic-actions-container')?.remove();
        return clone.innerText.trim();
    };

    // ASK AI
    if (e.target.closest('.ask-ai-topic-button')) {
        const topic = getTopicText();
        if (!topic) return;

        const query = `Explain this in detail: ${topic}`;

        window.Android?.askAI
            ? Android.askAI(query)
            : alert(query);

        return;
    }

    // YOUTUBE
    if (e.target.closest('.search-youtube-button')) {
        const topic = getTopicText();
        if (!topic) return;

        const url = `https://www.youtube.com/results?search_query=${encodeURIComponent(topic)}`;

        window.Android?.openYoutube
            ? Android.openYoutube(topic)
            : window.open(url);

        return;
    }
});  