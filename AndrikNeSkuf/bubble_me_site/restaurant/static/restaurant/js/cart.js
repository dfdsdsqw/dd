(function () {
    'use strict';

    var KEY = 'bubbleCart';
    var ORDERS_KEY = 'bubbleOrders';      // [{n, t, p:{name, phone, email}}]
    var PROFILE_KEY = 'bubbleProfile';    // збережені ПІДТВЕРДЖЕНІ дані клієнта
    var COLLAPSED_KEY = 'bubbleTrackCollapsed';
    var en = document.documentElement.lang === 'en';

    var T = {
        uah: en ? 'UAH' : 'грн',
        add: en ? 'Add to cart' : 'Додати в кошик',
        added: en ? 'Added to cart' : 'Додано в кошик',
        empty: en ? 'Your cart is empty' : 'Кошик порожній',
        emptyHint: en ? 'Pick something tasty from the menu' : 'Обери щось смачненьке з меню',
        toMenu: en ? 'Go to menu' : 'Перейти до меню',
        standard: en ? 'Standard' : 'Стандарт',
        choose: en ? 'Choose size' : 'Оберіть розмір',
        unavailable: en ? 'Price is not set yet' : 'Ціна ще не вказана',
        cart: en ? 'Cart' : 'Кошик',
        checkoutTitle: en ? 'Checkout' : 'Оформлення замовлення',
        checkout: en ? 'Place order' : 'Оформити замовлення',
        confirm: en ? 'Confirm order' : 'Підтвердити замовлення',
        sending: en ? 'Sending…' : 'Надсилаємо…',
        total: en ? 'Total' : 'Разом',
        errName: en ? 'Please enter your name' : "Введіть ім'я",
        errPhone: en ? 'Enter your phone number' : 'Введіть номер телефону',
        phoneShort: en ? 'The number is incomplete' : 'Номер неповний',
        phoneUnknown: en ? 'Number not found: no such operator code' : 'Номер не знайдено: такого коду оператора не існує',
        phoneTooMany: en ? 'Too many digits. Number not found' : 'Забагато цифр. Номер не знайдено',
        errEmail: en ? 'Enter a valid email' : 'Введіть коректний email',
        errNetwork: en ? 'Could not send the order. Please try again.' : 'Не вдалося надіслати замовлення. Спробуйте ще раз.',
        mailSent: en ? 'We sent a confirmation to ' : 'Ми надіслали лист на ',
        verifyHint: en ? 'Confirm your email via the link in the message and next time we will fill in your details automatically.'
                       : 'Підтвердіть пошту за посиланням у листі, і наступного разу ми самі заповнимо ваші дані.',
        orderWord: en ? 'Order No.' : 'Замовлення №',
        eta: en ? 'Estimated time: ~' : 'Орієнтовний час: ~',
        min: en ? ' min' : ' хв',
        readyToast: en ? 'Your order is ready! Come and pick it up' : 'Ваше замовлення готове! Чекаємо на вас'
    };

    var STATUS_LABEL = {
        new: en ? 'Received' : 'Прийнято',
        processing: en ? 'Being prepared' : 'Готується',
        ready: en ? 'Ready for pickup!' : 'Готове! Чекає на видачу',
        done: en ? 'Picked up' : 'Видано',
        cancelled: en ? 'Cancelled' : 'Скасовано'
    };
    var STEPS = ['new', 'processing', 'ready', 'done'];
    var STEP_LABEL = en ? ['Received', 'Preparing', 'Ready', 'Picked up'] : ['Прийнято', 'Готується', 'Готове', 'Видано'];

    var MOBILE_CODES = ['39', '50', '63', '66', '67', '68', '73', '91', '92', '93', '94', '95', '96', '97', '98', '99'];

    var menuHref = document.getElementById('menu') ? '#menu' : '/#menu';

    /* ---------- Загальні помічники ---------- */
    function esc(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function money(n) {
        var s = (Math.round(n * 100) / 100).toFixed(2).replace(/\.00$/, '');
        if (!en) s = s.replace('.', ',');
        return s + ' ' + T.uah;
    }

    function loadJSON(key, fallback) {
        try {
            var v = JSON.parse(localStorage.getItem(key));
            return v === null || v === undefined ? fallback : v;
        } catch (e) { return fallback; }
    }

    function saveJSON(key, value) {
        try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
    }

    function load() { return loadJSON(KEY, []); }

    function save(cart) {
        saveJSON(KEY, cart);
        render();
    }

    function csrfToken() {
        var el = document.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }

    function toast(text, ms) {
        var t = document.createElement('div');
        t.className = 'toast';
        t.textContent = text;
        document.body.appendChild(t);
        setTimeout(function () { t.remove(); }, ms || 1600);
    }

    /* ---------- Меню-бургер ---------- */
    var burger = document.getElementById('burger');
    var nav = document.getElementById('mainNav');
    if (burger && nav) {
        burger.addEventListener('click', function () {
            var open = nav.classList.toggle('open');
            burger.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
        nav.addEventListener('click', function (e) {
            if (e.target.closest('a')) {
                nav.classList.remove('open');
                burger.setAttribute('aria-expanded', 'false');
            }
        });
    }

    /* ---------- Маска телефону +380 __ ___ __ __ ---------- */
    var phoneInput = document.getElementById('f_phone');
    var phoneState = { digits: '', overflow: false };

    // Дістає цифри номера з будь-якого тексту: введеного вручну або вставленого
    function parsePhone(raw) {
        var hasPrefix = raw.indexOf('+380') === 0;
        var d = (hasPrefix ? raw.slice(4) : raw).replace(/\D/g, '');
        if (!hasPrefix && d.indexOf('380') === 0) d = d.slice(3);
        if (d.indexOf('380') === 0 && d.length > 9) d = d.slice(3);  // вставили +380... поверх маски
        d = d.replace(/^0+/, '');                                      // 0 перед кодом оператора не потрібен
        return { digits: d.slice(0, 9), overflow: d.length > 9 };
    }

    // Малює маску: введені цифри замінюють підкреслення по одній
    function formatPhone(d) {
        var groups = [2, 3, 2, 2], pos = 0, out = '+380 ', caret = 5;
        for (var g = 0; g < groups.length; g++) {
            for (var k = 0; k < groups[g]; k++) {
                var ch = d.charAt(pos++);
                out += ch || '_';
                if (ch) caret = out.length;
            }
            if (g < groups.length - 1) out += ' ';
        }
        return { text: out, caret: caret };
    }

    function phoneProblem(final) {
        var d = phoneState.digits;
        if (phoneState.overflow) return T.phoneTooMany;
        if (d.length >= 2 && '38'.indexOf(d) !== 0 && MOBILE_CODES.indexOf(d.slice(0, 2)) === -1) return T.phoneUnknown;
        if (final) {
            if (!d.length) return T.errPhone;
            if (d.length < 9) return T.phoneShort;
        }
        return '';
    }

    function showPhoneStatus(final) {
        if (!phoneInput) return '';
        var problem = phoneProblem(final);
        var box = document.querySelector('[data-error="phone"]');
        if (box) { box.textContent = problem; box.hidden = !problem; }
        phoneInput.classList.toggle('invalid', !!problem);
        phoneInput.classList.toggle('valid', !problem && phoneState.digits.length === 9);
        return problem;
    }

    function renderPhone() {
        var f = formatPhone(phoneState.digits);
        phoneInput.value = f.text;
        if (document.activeElement === phoneInput) {
            try { phoneInput.setSelectionRange(f.caret, f.caret); } catch (e) {}
        }
    }

    function setPhone(value) {
        phoneState = parsePhone(String(value || ''));
        if (phoneState.digits.length) renderPhone(); else phoneInput.value = '';
        showPhoneStatus(false);
    }

    function fixCaret() {
        var f = formatPhone(phoneState.digits);
        setTimeout(function () {
            try { phoneInput.setSelectionRange(f.caret, f.caret); } catch (e) {}
        }, 0);
    }

    if (phoneInput) {
        phoneInput.addEventListener('focus', function () {
            if (!phoneState.digits.length) renderPhone();
            fixCaret();
        });
        phoneInput.addEventListener('blur', function () {
            if (!phoneState.digits.length) phoneInput.value = '';
            if (phoneState.digits.length) showPhoneStatus(true);
        });
        ['input', 'change'].forEach(function (ev) {
            phoneInput.addEventListener(ev, function () {
                phoneState = parsePhone(phoneInput.value);
                renderPhone();
                showPhoneStatus(false);
            });
        });
        ['mouseup', 'touchend', 'keyup'].forEach(function (ev) {
            phoneInput.addEventListener(ev, fixCaret);
        });
    }

    /* ---------- Кошик (на весь екран) ---------- */
    var cartWin = document.getElementById('cartWindow');
    var cartToggle = document.getElementById('cartToggle');
    var cartList = document.getElementById('cartItems');
    var cartFoot = document.getElementById('cartFoot');
    var cartView = document.getElementById('cartView');
    var cartBody = document.getElementById('cartBody');
    var form = document.getElementById('checkoutForm');
    var doneView = document.getElementById('doneView');
    var backBtn = document.getElementById('cartBack');
    var titleEl = document.getElementById('cartTitle');
    var orderBtn = document.getElementById('cartOrderBtn');
    var formError = document.getElementById('formError');
    var fName = document.getElementById('f_name');
    var fEmail = document.getElementById('f_email');
    var state = 'list'; // list | form | done
    var sending = false;

    function updateFoot() {
        var hasItems = load().length > 0;
        cartFoot.hidden = !((state === 'list' && hasItems) || state === 'form');
        if (!sending) orderBtn.textContent = state === 'form' ? T.confirm : T.checkout;
    }

    // Підставляє збережені підтверджені дані клієнта
    function applyProfile() {
        var note = document.getElementById('profileNote');
        var p = loadJSON(PROFILE_KEY, null);
        if (p && p.email) {
            if (!fName.value) fName.value = p.name || '';
            if (!fEmail.value) fEmail.value = p.email;
            if (!phoneState.digits.length && p.phone) setPhone(p.phone);
            note.hidden = false;
        } else {
            note.hidden = true;
        }
    }

    function setState(s) {
        state = s;
        cartView.hidden = s !== 'list';
        form.hidden = s !== 'form';
        doneView.hidden = s !== 'done';
        backBtn.hidden = s !== 'form';
        titleEl.textContent = s === 'form' ? T.checkoutTitle : T.cart;
        if (s === 'form') { renderSummary(); applyProfile(); }
        updateFoot();
        cartBody.scrollTop = 0;
    }

    function openCart() {
        setState('list');
        render();
        cartWin.hidden = false;
        cartToggle.setAttribute('aria-expanded', 'true');
        document.body.classList.add('no-scroll');
    }

    function closeCart() {
        cartWin.hidden = true;
        cartToggle.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('no-scroll');
    }

    function renderSummary() {
        var cart = load(), total = 0;
        var html = cart.map(function (i) {
            total += i.qty * i.price;
            return '<div class="order-line"><span>' + esc(i.title) +
                (i.variant ? ' (' + esc(i.variant) + ')' : '') + ' × ' + i.qty +
                '</span><span>' + money(i.qty * i.price) + '</span></div>';
        }).join('');
        html += '<div class="order-line total"><span>' + T.total + '</span><span>' + money(total) + '</span></div>';
        document.getElementById('orderSummary').innerHTML = html;
    }

    function clearErrors() {
        form.querySelectorAll('[data-error]').forEach(function (el) { el.hidden = true; el.textContent = ''; });
        formError.hidden = true;
        formError.textContent = '';
    }

    function showErrors(errs) {
        var general = '';
        Object.keys(errs).forEach(function (k) {
            var el = form.querySelector('[data-error="' + k + '"]');
            if (el) { el.textContent = errs[k]; el.hidden = false; }
            else general = errs[k];
        });
        if (general) { formError.textContent = general; formError.hidden = false; }
        var first = form.querySelector('.field-error:not([hidden])');
        if (first && first.scrollIntoView) first.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }

    function rememberOrder(entry, verified) {
        var list = loadJSON(ORDERS_KEY, []);
        list.unshift(entry);
        saveJSON(ORDERS_KEY, list.slice(0, 10));
        if (verified) saveJSON(PROFILE_KEY, entry.p);
    }

    function submitOrder() {
        if (sending) return;
        var cart = load();
        if (!cart.length) { setState('list'); render(); return; }
        clearErrors();

        var profile = {
            name: fName.value.trim(),
            phone: '+380' + phoneState.digits,
            email: fEmail.value.trim().toLowerCase()
        };
        var payload = {
            name: profile.name,
            phone: profile.phone,
            email: profile.email,
            comment: document.getElementById('f_comment').value.trim(),
            hp: document.getElementById('f_hp').value,
            items: cart.map(function (i) {
                var p = String(i.key).split('-');
                return { item: p[0], variant: p[1] || '0', qty: i.qty };
            })
        };

        var errs = {};
        if (!payload.name) errs.name = T.errName;
        var phoneMsg = showPhoneStatus(true);
        if (phoneMsg) errs.phone = phoneMsg;
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.email)) errs.email = T.errEmail;
        if (Object.keys(errs).length) { showErrors(errs); return; }

        sending = true;
        orderBtn.disabled = true;
        orderBtn.textContent = T.sending;

        fetch(form.dataset.url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
            body: JSON.stringify(payload)
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.ok) {
                rememberOrder({ n: data.number, t: data.token, p: profile, ts: Date.now() }, data.verified);
                document.getElementById('doneNumber').textContent = '№' + data.number;
                document.getElementById('doneMail').textContent =
                    T.mailSent + profile.email + '. ' + (data.verified ? '' : T.verifyHint);
                document.getElementById('f_comment').value = '';
                sending = false;
                save([]);
                setState('done');
                pollStatus();
            } else {
                showErrors(data.errors || { items: T.errNetwork });
            }
        })
        .catch(function () { showErrors({ items: T.errNetwork }); })
        .then(function () {
            sending = false;
            orderBtn.disabled = false;
            updateFoot();
        });
    }

    if (cartWin && cartToggle) {
        cartToggle.addEventListener('click', function () {
            if (cartWin.hidden) openCart(); else closeCart();
        });
        document.getElementById('cartClose').addEventListener('click', closeCart);
        backBtn.addEventListener('click', function () { setState('list'); });

        orderBtn.addEventListener('click', function () {
            if (state === 'list') { if (load().length) setState('form'); }
            else if (state === 'form') submitOrder();
        });
        form.addEventListener('submit', function (e) { e.preventDefault(); submitOrder(); });

        document.getElementById('profileClear').addEventListener('click', function () {
            try { localStorage.removeItem(PROFILE_KEY); } catch (e) {}
            fName.value = '';
            fEmail.value = '';
            setPhone('');
            document.getElementById('profileNote').hidden = true;
        });

        cartWin.addEventListener('click', function (e) {
            if (e.target.closest('[data-go-menu]') || e.target.closest('[data-close-cart]')) { closeCart(); return; }
            var b = e.target.closest('button[data-act]');
            if (!b) return;
            var cart = load();
            var idx = cart.findIndex(function (i) { return i.key === b.dataset.key; });
            if (idx < 0) return;
            if (b.dataset.act === 'inc') cart[idx].qty++;
            if (b.dataset.act === 'dec') cart[idx].qty--;
            if (b.dataset.act === 'del' || cart[idx].qty < 1) cart.splice(idx, 1);
            save(cart);
        });
    }

    function render() {
        var cart = load();
        var count = 0, total = 0;
        cart.forEach(function (i) { count += i.qty; total += i.qty * i.price; });

        var badge = document.getElementById('cartCount');
        if (badge) { badge.textContent = count; badge.hidden = count === 0; }

        var totalEl = document.getElementById('cartTotal');
        if (totalEl) totalEl.textContent = money(total);

        if (!cartList) return;

        if (!cart.length) {
            cartList.innerHTML =
                '<div class="cart-empty">' +
                    '<div class="cart-empty-title">' + T.empty + '</div>' +
                    '<p>' + T.emptyHint + '</p>' +
                    '<a class="btn-bubble" href="' + menuHref + '" data-go-menu>' + T.toMenu + '</a>' +
                '</div>';
        } else {
            cartList.innerHTML = cart.map(function (i) {
                return '<div class="cart-row">' +
                    '<div class="cart-info">' +
                        '<div class="cart-name">' + esc(i.title) + '</div>' +
                        (i.variant ? '<div class="cart-variant">' + esc(i.variant) + '</div>' : '') +
                        '<div class="cart-price">' + money(i.price) + '</div>' +
                    '</div>' +
                    '<div class="qty">' +
                        '<button type="button" data-act="dec" data-key="' + esc(i.key) + '">−</button>' +
                        '<span>' + i.qty + '</span>' +
                        '<button type="button" data-act="inc" data-key="' + esc(i.key) + '">+</button>' +
                    '</div>' +
                    '<button type="button" class="cart-del" data-act="del" data-key="' + esc(i.key) + '" aria-label="Remove">✕</button>' +
                '</div>';
            }).join('');
        }
        if (cartFoot) updateFoot();
    }

    /* ---------- Відстеження замовлення ---------- */
    var tracker = document.getElementById('tracker');
    var trackerList = document.getElementById('trackerList');
    var lastStatus = {};
    var pollTimer = null;

    function stepsHtml(status) {
        var idx = STEPS.indexOf(status);
        return '<div class="steps">' + STEPS.map(function (s, i) {
            var cls = i < idx ? 'done' : (i === idx ? 'now' : '');
            return '<div class="step ' + cls + '"><span class="dot"></span>' + STEP_LABEL[i] + '</div>';
        }).join('') + '</div>';
    }

    function renderTracker(orders) {
        if (!tracker) return;
        var collapsed = loadJSON(COLLAPSED_KEY, []);
        var visible = orders.filter(function (o) {
            return (o.status !== 'done' && o.status !== 'cancelled') || o.age_minutes < 60;
        }).sort(function (a, b) { return b.number - a.number; }).slice(0, 3);

        if (!visible.length) { tracker.hidden = true; return; }

        trackerList.innerHTML = visible.map(function (o) {
            var isCollapsed = collapsed.indexOf(o.token) !== -1;
            var body = '';
            if (o.status !== 'cancelled') body += stepsHtml(o.status);
            if (o.eta && (o.status === 'new' || o.status === 'processing')) {
                body += '<div class="track-eta">' + T.eta + o.eta + T.min + '</div>';
            }
            body += '<ul class="track-items">' + o.items.map(function (i) {
                return '<li>' + esc(i.title) + (i.variant ? ' (' + esc(i.variant) + ')' : '') + ' × ' + i.qty + '</li>';
            }).join('') + '</ul>';
            body += '<div class="track-total">' + T.total + ': ' + money(parseFloat(o.total)) + '</div>';

            return '<div class="track-card s-' + esc(o.status) + '">' +
                '<button type="button" class="track-head" data-track="' + esc(o.token) + '">' +
                    '<span class="track-title">' + T.orderWord + o.number + '</span>' +
                    '<span class="track-badge">' + esc(STATUS_LABEL[o.status] || o.status) + '</span>' +
                '</button>' +
                (isCollapsed ? '' : '<div class="track-body">' + body + '</div>') +
            '</div>';
        }).join('');
        tracker.hidden = false;
    }

    if (trackerList) {
        trackerList.addEventListener('click', function (e) {
            var head = e.target.closest('[data-track]');
            if (!head) return;
            var collapsed = loadJSON(COLLAPSED_KEY, []);
            var i = collapsed.indexOf(head.dataset.track);
            if (i === -1) collapsed.push(head.dataset.track); else collapsed.splice(i, 1);
            saveJSON(COLLAPSED_KEY, collapsed);
            pollStatus();
        });
    }

    function handleStatus(known, orders) {
        var byToken = {};
        orders.forEach(function (o) { byToken[o.token] = o; });

        // Забуваємо записи старші за 8 днів (сервер показує замовлення лише за 7 днів)
        var kept = known.filter(function (k) { return !k.ts || Date.now() - k.ts < 8 * 24 * 3600 * 1000; });
        if (kept.length !== known.length) saveJSON(ORDERS_KEY, kept);

        // Пошта підтверджена за посиланням з листа: запам'ятовуємо дані як шаблон
        kept.forEach(function (k) {
            var o = byToken[k.t];
            if (o && o.verified && k.p && !loadJSON(PROFILE_KEY, null)) saveJSON(PROFILE_KEY, k.p);
        });

        // Повідомлення, коли замовлення стало «готове»
        orders.forEach(function (o) {
            var prev = lastStatus[o.token];
            if (prev && prev !== o.status && o.status === 'ready') {
                toast(T.readyToast, 7000);
                if (navigator.vibrate) { try { navigator.vibrate([200, 100, 200]); } catch (err) {} }
            }
            lastStatus[o.token] = o.status;
        });

        renderTracker(orders);
    }

    function pollStatus() {
        var known = loadJSON(ORDERS_KEY, []);
        if (!form || !known.length) { if (tracker) tracker.hidden = true; return; }
        fetch(form.dataset.statusUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
            body: JSON.stringify({ tokens: known.map(function (k) { return k.t; }) })
        })
        .then(function (r) { return r.json(); })
        .then(function (data) { handleStatus(known, data.orders || []); })
        .catch(function () {});
    }

    function startPolling() {
        pollStatus();
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(function () { if (!document.hidden) pollStatus(); }, 20000);
    }

    /* ---------- Вікно позиції меню ---------- */
    var overlay = document.getElementById('itemOverlay');
    var body = document.getElementById('itemBody');

    function closeItem() {
        overlay.hidden = true;
        document.body.classList.remove('no-scroll');
        body.onclick = null;
    }

    function openItem(card) {
        var options = [];
        card.querySelectorAll('.variant-row').forEach(function (r) {
            options.push({ id: r.dataset.id, name: r.dataset.name || '', price: parseFloat(r.dataset.price) });
        });
        if (!options.length && card.dataset.price) {
            options.push({ id: '0', name: '', price: parseFloat(card.dataset.price) });
        }

        var selected = 0, qty = 1;
        var title = card.dataset.title;

        function draw() {
            var html = card.dataset.img
                ? '<img class="item-img" src="' + esc(card.dataset.img) + '" alt="">'
                : '<div class="img-placeholder">🥤</div>';
            html += '<div class="item-content"><h3>' + esc(title) + '</h3>';
            if (card.dataset.desc) html += '<p>' + esc(card.dataset.desc) + '</p>';

            if (options.length > 1) {
                html += '<div class="opt-label">' + T.choose + '</div><div class="opt-list">';
                options.forEach(function (o, i) {
                    html += '<button type="button" class="opt' + (i === selected ? ' active' : '') + '" data-opt="' + i + '">' +
                            '<span>' + esc(o.name || T.standard) + '</span><span>' + money(o.price) + '</span></button>';
                });
                html += '</div>';
            }

            if (options.length) {
                html += '<div class="item-footer">' +
                    '<div class="qty"><button type="button" data-q="-1">−</button><span>' + qty + '</span><button type="button" data-q="1">+</button></div>' +
                    '<button type="button" class="btn-bubble" data-add="1">' + T.add + ' · ' + money(options[selected].price * qty) + '</button>' +
                    '</div>';
            } else {
                html += '<p>' + T.unavailable + '</p>';
            }
            html += '</div>';
            body.innerHTML = html;
        }

        body.onclick = function (e) {
            var opt = e.target.closest('[data-opt]');
            var q = e.target.closest('[data-q]');
            var add = e.target.closest('[data-add]');
            if (opt) { selected = parseInt(opt.dataset.opt, 10); draw(); }
            if (q) { qty = Math.max(1, qty + parseInt(q.dataset.q, 10)); draw(); }
            if (add) {
                var o = options[selected];
                var key = card.dataset.id + '-' + o.id;
                var cart = load();
                var existing = cart.find(function (i) { return i.key === key; });
                if (existing) existing.qty += qty;
                else cart.push({ key: key, title: title, variant: o.name, price: o.price, qty: qty });
                save(cart);
                closeItem();
                toast(T.added);

                var badge = document.getElementById('cartCount');
                if (badge) {
                    badge.classList.remove('bump');
                    void badge.offsetWidth;
                    badge.classList.add('bump');
                }
            }
        };

        draw();
        overlay.hidden = false;
        document.body.classList.add('no-scroll');
    }

    if (overlay && body) {
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay || e.target.closest('[data-close]')) closeItem();
        });

        document.addEventListener('click', function (e) {
            var card = e.target.closest('.menu-card');
            if (card) openItem(card);
        });

        document.addEventListener('keydown', function (e) {
            var el = e.target;
            if ((e.key === 'Enter' || e.key === ' ') && el.classList && el.classList.contains('menu-card')) {
                e.preventDefault();
                openItem(el);
            }
        });
    }

    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        if (overlay && !overlay.hidden) closeItem();
        else if (cartWin && !cartWin.hidden) closeCart();
    });

    render();
    startPolling();
})();
