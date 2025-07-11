const container = document.getElementById("container");
const maxComments = 10;

function createCommentElement(username, text) {
    const div = document.createElement("div");
    div.classList.add("comment", "comment-enter-from", "comment-enter-active");
    div.style.top = "0px";
    div.style.opacity = "0";
    div.style.transform = "translateX(100%)";
    
    // ユーザー名部分（太字などにしたい場合）
    const nameEl = document.createElement("div");
    nameEl.classList.add("comment-username");
    nameEl.textContent = username;

    // コメント本文
    const messageEl = document.createElement("div");
    messageEl.classList.add("comment-message");
    messageEl.textContent = text;

    // 要素を結合
    
    div.appendChild(messageEl);
    div.appendChild(nameEl);

    return div;
}

function shiftExistingCommentsUp(newHeight) {
    const comments = Array.from(container.querySelectorAll(".comment"));
    comments.forEach(el => {
        const currentTop = parseInt(el.style.top || "0", 10);
        el.style.top = (currentTop - newHeight - 10) + "px";
    });
}

function removeOldestIfNecessary() {
    const comments = container.querySelectorAll(".comment");
    if (comments.length >= maxComments) {
        comments[0].remove();
    }
}

function AddComment(username, comment) {
    if (!comment) return;

    const newComment = createCommentElement(username, comment);
    container.appendChild(newComment);

    requestAnimationFrame(() => {
        const newHeight = newComment.offsetHeight;
        shiftExistingCommentsUp(newHeight);
        removeOldestIfNecessary();

        newComment.classList.remove("comment-enter-from");
        newComment.style.transform = "translateX(0)";
        newComment.style.opacity = "1";
    });
}
