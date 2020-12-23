
async function editBot(botLogin, values) {
    return await fetch("/api/bot", {
        "method": "POST",
        "headers": {
            "Content-Type": 'application/json'
        },
        "body": JSON.stringify({
            "login": botLogin,
            ...values
        })
    });
}

async function deleteBot(botLogin) {
    await fetch("/api/bot", {
        "method": "DELETE",
        "headers": {
            "Content-Type": 'application/json'
        },
        "body": JSON.stringify({
            "login": botLogin
        })
    });
    document.location.reload();
}

async function changeBotState(botLogin) {
    botStateCheckbox = document.getElementById(botLogin);
    const response = await editBot(botLogin, {state: botStateCheckbox.checked});

    if (!response || response.status !== 200)
        botStateCheckbox.checked = false;
}

async function addBot(botLogin = "add-bot") {
    let newBotLogin;

    if (botLogin === "add-bot") {
        const loginInput = document.getElementById(`${botLogin}-login`);

        if (!loginInput.value)
            return;

        newBotLogin = loginInput.value;
    } else {
        newBotLogin = botLogin;
    }

    const passwordInput = document.getElementById(`${botLogin}-password`);
    const steamidInput = document.getElementById(`${botLogin}-steamid`);
    const sharedSecretInput = document.getElementById(`${botLogin}-sharedsecret`);
    const indetitySecretInput = document.getElementById(`${botLogin}-indetitysecret`);
    const apiKeyInput = document.getElementById(`${botLogin}-apikey`);
    const tmapiKeyInput = document.getElementById(`${botLogin}-tmapikey`);
    const googleDocIdInput = document.getElementById(`${botLogin}-googledocid`);
    const proxyInput = document.getElementById(`${botLogin}-proxy`);

    await editBot(newBotLogin, {
        password: passwordInput.value,
        steamid: steamidInput.value,
        shared_secret: sharedSecretInput.value,
        identity_secret: indetitySecretInput.value,
        steam_api_key: apiKeyInput.value,
        tm_api_key: tmapiKeyInput.value,
        google_doc_id: googleDocIdInput.value,
        proxy: proxyInput.value
    });

    document.location.reload();
}
