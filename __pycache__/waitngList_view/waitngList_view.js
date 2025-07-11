function WaitingListView(usernames) {
    // コンテナをクリア
    $('#container').empty();

    // null や undefined、または空配列チェック
    if (!Array.isArray(usernames) || usernames.length === 0) {
        return;
    }

    // 各ユーザー名を順番に表示
    usernames.forEach(function (name) {
        const userDiv = $('<div></div>').text(name);
        $('#container').append(userDiv);
    });
}