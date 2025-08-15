document.addEventListener('DOMContentLoaded', function() {
    // Hiệu ứng cho nút engagement
    const engagementBtns = document.querySelectorAll('.engagement-btn');
    engagementBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            this.classList.toggle('active');

            // Nếu là nút like
            if (this.textContent.includes('❤️')) {
                const currentCount = parseInt(this.textContent.match(/\d+/));
                const newCount = this.classList.contains('active') ?
                    currentCount + 1 : currentCount - 1;

                this.innerHTML = `❤️ ${newCount}`;

                // Hiệu ứng tim scale
                this.style.transform = this.classList.contains('active')
                    ? 'scale(1.2)' : 'scale(0.9)';
                setTimeout(() => {
                    this.style.transform = 'scale(1)';
                }, 200);
            }
        });
    });

    // Hiệu ứng cho menu
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', function() {
            menuItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // Nút đăng bài
    const postBtn = document.querySelector('.post-btn');
    const textarea = document.querySelector('.post-textarea');
    const imageInput = document.getElementById('image-upload');
    
    postBtn.addEventListener('click', function(event) {
        const hasText = textarea.value.trim() !== '';
        const hasImage = imageInput.files.length > 0;
    
        if (!hasText && !hasImage) {
            event.preventDefault(); // Chặn submit nếu rỗng cả text và ảnh
            alert('Vui lòng nhập nội dung hoặc chọn ảnh trước khi đăng!');
            return;
        }
    });

    // Hiệu ứng search
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('focus', function() {
            this.style.background = 'rgba(255, 255, 255, 0.9)';
        });
        searchInput.addEventListener('blur', function() {
            this.style.background = 'rgba(102, 126, 234, 0.1)';
        });
    }

    // Smooth scroll cho post mới
    const posts = document.querySelectorAll('.post');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    posts.forEach(post => observer.observe(post));
});

// CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(100%); }
        to { opacity: 1; transform: translateX(0); }
    }
`;
document.head.appendChild(style);
