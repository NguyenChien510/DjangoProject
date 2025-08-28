const CURRENT_USER_NAME = "{{ request.user.full_name|escapejs }}";
const CURRENT_USER_ID = parseInt("{{ request.user.id }}", 10);
const CURRENT_USER_AVATAR = "{{ request.user.avatar.url|default_if_none:'null' }}";
let currentUserId = null;
let currentConversationId = null;
let chatSocket = null;

function selectChat(otherId, otherName, convId,otherAvatarUrl = null) {
    currentUserId = otherId;
    currentConversationId = convId;

    document.getElementById("headerName").textContent = otherName;
    document.querySelector('.header-status').textContent = 'Đang tải...';
    
    const avatarDiv = document.getElementById("headerAvatar");
    avatarDiv.innerHTML = ""; // xóa nội dung cũ
    if (otherAvatarUrl&& otherAvatarUrl !== "null") {
        const img = document.createElement("img");
        img.src = otherAvatarUrl;
        img.alt = otherName;
        img.style.width = "100%";
        img.style.height = "100%";
        img.style.objectFit = "cover";
        img.style.borderRadius = "50%";
        avatarDiv.appendChild(img);
    } else {
        avatarDiv.textContent = otherName.charAt(0).toUpperCase();
    }

    const container = document.getElementById("messagesContainer");
    container.innerHTML = "<p>Đang tải tin nhắn...</p>";

        // Load trạng thái ban đầu
        fetch(`/chat/status/${otherId}/`)
        .then(res => res.json())
        .then(data => {
            document.querySelector('.header-status').textContent = data.status;
        })
        .catch(() => {
            document.querySelector('.header-status').textContent = "Không lấy được trạng thái";
        });

    // Nếu muốn auto update status mỗi 15s
    if (window.statusInterval) clearInterval(window.statusInterval);
    window.statusInterval = setInterval(() => {
        fetch(`/chat/status/${otherId}/`)
            .then(res => res.json())
            .then(data => {
                document.querySelector('.header-status').textContent = data.status;
            });
    }, 15000);
    // Load tin nhắn cũ
    fetch(`/chat/messages/${convId}/`)
        .then(res => res.json())
        .then(data => {
            container.innerHTML = "";
            data.forEach(m => {
                addMessage(m.text, m.sender_name,   m.is_self , m.time,m.sender_avatar);
            });
        })
        .catch(err => {
            console.error("Error loading messages:", err);
            container.innerHTML = "<p>Lỗi khi tải tin nhắn</p>";
        });

    // WebSocket
    if (chatSocket) chatSocket.close();
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    chatSocket = new WebSocket(`${protocol}://${window.location.host}/ws/chat/${convId}/`);

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.type === "chat_message") {
            addMessage( 
                data.message,
                data.sender_name,
                data.is_self ?? (data.sender_id === CURRENT_USER_ID),
                data.time,
                data.avatar);
        }
    };

    chatSocket.onclose = function() {
        console.error("Chat socket closed unexpectedly");
    };
}

function addMessage(text, senderName, isSelf = false, time = null,senderAvatarUrl = null) {
    const messagesContainer = document.getElementById('messagesContainer');
    const messageTime = time || new Date().toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit'
    });

    let avatarHtml = "";
    if (!isSelf) {
        if (senderAvatarUrl && senderAvatarUrl !== "null") {
            avatarHtml = `<img src="${senderAvatarUrl}" alt="${senderName}" 
                               style="width:32px;height:32px;border-radius:50%;object-fit:cover;">`;
        } else {
            avatarHtml = senderName.charAt(0).toUpperCase();
        }
    }

    const html = isSelf ? `
        <div class="message sent">
            <div class="message-content">${text}</div>
        </div>
        <div class="message-time" style="text-align: right; margin-right: 12px;">${messageTime}</div>
    ` : `
        <div class="message received">
            <div class="message-avatar">${avatarHtml}</div>
            <div class="message-content">${text}</div>
        </div>
        <div class="message-time" style="text-align: left; margin-left: 44px;">${messageTime}</div>
    `;
    messagesContainer.innerHTML += html;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const messageText = messageInput.value.trim();
    if (!chatSocket || !messageText) return;

    chatSocket.send(JSON.stringify({ message: messageText ,avatar: CURRENT_USER_AVATAR}));
    messageInput.value = '';
    messageInput.style.height = "auto";
}

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

// Search user
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

function openOrSelectConversation(userId, userName) {
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

    fetch(`/chat/get-or-create-conversation/${userId}/`)
        .then(res => res.json())
        .then(data => {
            const convId = data.id;
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
