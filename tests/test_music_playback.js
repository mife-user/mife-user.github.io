// 在 Node.js 中模拟媒体事件，检查正文播放器和背景音乐的互斥逻辑。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const footer = fs.readFileSync(path.join(__dirname, '../themes/mife-theme/layouts/partials/footer.html'), 'utf8');

function section(start, end) {
    const from = footer.indexOf(start);
    const to = footer.indexOf(end, from);
    assert.ok(from >= 0 && to > from, `找不到待测试的脚本片段: ${start}`);
    return footer.slice(from, to);
}

function audio(embedded, paused = false) {
    return {
        paused,
        classList: { contains: name => embedded && name === 'embedded-audio-element' },
        pause() { this.paused = true; },
        play() { this.paused = false; return Promise.resolve(); }
    };
}

async function main() {
    const first = audio(true), second = audio(true), background = audio(false);
    const players = [first, second];
    let handler, state;
    const document = {
        addEventListener(type, callback, capture) {
            assert.equal(type, 'play');
            assert.equal(capture, true);
            handler = callback;
        },
        querySelectorAll(selector) {
            assert.equal(selector, '.embedded-audio-element');
            return players;
        }
    };
    const context = { document, bgMusic: background, setPlayState: playing => { state = playing; } };
    vm.createContext(context);
    vm.runInContext(section('    function playTrack() {', '    function toggleMusic() {'), context);

    handler({ target: first });
    assert.equal(first.paused, false);
    assert.equal(second.paused, true);
    assert.equal(background.paused, true);
    assert.equal(state, false);

    first.paused = false;
    second.paused = false;
    background.paused = false;
    handler({ target: background });
    assert.equal(first.paused, true);
    assert.equal(second.paused, true);
    assert.equal(background.paused, false);

    first.paused = false;
    background.paused = false;
    handler({ target: audio(false) });
    assert.equal(first.paused, false);
    assert.equal(background.paused, false);

    first.paused = true;
    handler({ target: first });
    assert.equal(background.paused, false); // 已过时的 play 事件不打断当前音频。

    background.play = () => { background.paused = true; return Promise.reject(new Error('blocked')); };
    context.playTrack();
    assert.equal(state, true);
    await Promise.resolve();
    assert.equal(state, false); // 背景播放被拒绝时恢复按钮状态。

    let load, calls = 0;
    const loadContext = {
        window: { addEventListener(type, callback) { assert.equal(type, 'load'); load = callback; } },
        document,
        playlist: ['track'],
        playTrack() { calls++; }
    };
    vm.runInNewContext(section('    // 页面加载完成后尝试自动播放', '    renderPlaylist();'), loadContext);
    first.paused = false;
    second.paused = true;
    load();
    assert.equal(calls, 0); // 加载时正文已在播放，不抢占。
    first.paused = true;
    load();
    assert.equal(calls, 1);
    loadContext.playlist = [];
    load();
    assert.equal(calls, 1);
    console.log('正文与背景音乐互斥逻辑测试通过');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
