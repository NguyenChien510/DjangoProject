const CURRENT_USER_NAME = "{{ current_user_name }}";
let currentUserId = null;
let currentConversationId = null;
let chatSocket = null;

// ======================
// Chọn chat
// ======================
function selectChat(otherId, otherName, convId) {
    currentUserId = otherId;
    currentConversationId = convId;

    // Cập nhật header
    document.getElementById("headerName").textContent = otherName;
    document.getElementById("headerAvatar").textContent = otherName.charAt(0);
    document.querySelector('.header-status').textContent = 'Đang tải...';

    // Clear tin nhắn cũ
    const container = document.getElementById("messagesContainer");
    container.innerHTML = "<p>Đang tải tin nhắn...</p>";

    // Load trạng thái người dùng
    fetch(`/chat/status/${otherId}/`)
        .then(res => res.json())
        .then(data => {
            document.querySelector('.header-status').textContent = data.status;
        })
        .catch(err => {
            console.error("Error loading status:", err);
            document.querySelector('.header-status').textContent = 'Offline';
        });

    // Load tin nhắn cũ
    fetch(`/chat/messages/${otherId}/`)
        .then(res => res.json())
        .then(data => {
            container.innerHTML = "";
            data.forEach(m => {
                addMessage(m.text, m.sender, m.sender === CURRENT_USER_NAME, m.time);
            });
        })
        .catch(err => {
            console.error("Error loading messages:", err);
            container.innerHTML = "<p>Lỗi khi tải tin nhắn</p>";
        });

    // Tạo WebSocket chat mới
    if (chatSocket) chatSocket.close();
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    chatSocket = new WebSocket(`${protocol}://${window.location.host}/ws/chat/conversation_${convId}/`);

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.type === "chat_message") {
            addMessage(data.message, data.sender, data.is_self);
        }
    };

    chatSocket.onclose = function() {
        console.error("Chat socket closed unexpectedly");
    };
}

// ======================
// Thêm tin nhắn vào UI
// ======================
function addMessage(text, sender, isSelf = false, time = null) {
    const messagesContainer = document.getElementById('messagesContainer');
    const messageTime = time || new Date().toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit'
    });

    const html = isSelf ? `
        <div class="message sent">
            <div class="message-content">${text}</div>
        </div>
        <div class="message-time" style="text-align: right; margin-right: 12px;">${messageTime}</div>
    ` : `
        <div class="message received">
            <div class="message-avatar">${sender.charAt(0)}</div>
            <div class="message-content">${text}</div>
        </div>
        <div class="message-time" style="text-align: left; margin-left: 44px;">${messageTime}</div>
    `;
    messagesContainer.innerHTML += html;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ======================
// Gửi tin nhắn
// ======================
function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const messageText = messageInput.value.trim();
    if (!chatSocket || !messageText) return;

    chatSocket.send(JSON.stringify({ message: messageText }));
    messageInput.value = '';
    messageInput.style.height = "auto";
}

// ======================
// Xử lý Enter và auto-resize textarea
// ======================
const messageInput = document.getElementById('messageInput');
messageInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
messageInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 80) + 'px';
});

// ======================
// Search user realtime
// ======================
const searchInput = document.querySelector('.search-input');
const chatList = document.getElementById('chatList');
const searchResults = document.querySelector('.search-results');

searchInput.addEventListener('input', function() {
    const keyword = this.value.trim();
    if (!keyword) {
        searchResults.innerHTML = "";
        return;
    }

    fetch(`/chat/search-users/?q=${encodeURIComponent(keyword)}`)
        .then(res => res.json())
        .then(users => {
            searchResults.innerHTML = "";
            users.forEach(user => {
                const item = document.createElement("div");
                item.className = "search-item";
                item.innerHTML = `
                    <div class="avatar">${user.name.charAt(0)}</div>
                    <div class="name">${user.name}</div>
                `;
                item.onclick = () => openOrSelectConversation(user.id, user.name);
                searchResults.appendChild(item);
            });
        });
});

// ======================
// Mở hoặc chọn conversation
// ======================
function openOrSelectConversation(userId, userName) {
    // Kiểm tra xem conversation đã có trong UI chưa
    const existingItem = Array.from(chatList.children).find(
        item => item.dataset.userId == userId
    );

    if (existingItem) {
        const convId = existingItem.dataset.convId;
        selectChat(userId, userName, convId);
        searchResults.innerHTML = "";
        searchInput.value = "";
        return;
    }

    // Nếu chưa có, gọi API tạo hoặc lấy conversation
    fetch(`/chat/get-or-create-conversation/${userId}/`)
        .then(res => res.json())
        .then(data => {
            const convId = data.id;

            // Tạo UI mới
            const newItem = document.createElement("div");
            newItem.className = "chat-item";
            newItem.dataset.userId = userId;
            newItem.dataset.convId = convId;
            newItem.onclick = () => selectChat(userId, userName, convId);
            newItem.innerHTML = `
                <div class="avatar">${userName.charAt(0)}</div>
                <div class="chat-info">
                    <div class="chat-name">${userName}</div>
                    <div class="chat-preview">(Chưa có tin nhắn)</div>
                </div>
            `;
            chatList.prepend(newItem);

            selectChat(userId, userName, convId);
            searchResults.innerHTML = "";
            searchInput.value = "";
        });
}
