/* PlayX MIDI mapping for Mixxx >= 2.4. Safe, explicit live commands only. */
var PlayX = {};
PlayX.connections = [];
PlayX.init = function () {
    for (var deck = 1; deck <= 2; deck++) {
        (function (number) {
            var group = '[Channel' + number + ']';
            var last = 0;
            var conn = engine.makeConnection(group, 'beat_active', function (value) {
                // 1 = forward beat; only report during actual playback.
                if (value === 1 && last !== 1 && engine.getValue(group, 'play') > 0) {
                    midi.sendShortMsg(0xB0, number === 1 ? 70 : 71, 127);
                }
                last = value;
            });
            PlayX.connections.push(conn);
            var loadConn = engine.makeConnection(group, 'track_loaded', function (loaded) {
                midi.sendShortMsg(0xB0, number === 1 ? 72 : 73, loaded > 0 ? 127 : 0);
            });
            PlayX.connections.push(loadConn);
        })(deck);
    }
};
PlayX.shutdown = function () {
    PlayX.connections.forEach(function (c) { c.disconnect(); });
    PlayX.connections = [];
};
PlayX.action = function (_channel, control, value, _status, _group) {
    if (value === 0) return;
    if (control === 20) engine.setValue('[Channel1]', 'LoadSelectedTrack', 1);
    if (control === 21) engine.setValue('[Channel2]', 'LoadSelectedTrack', 1);
    if (control === 22) {
        engine.setValue('[Channel2]', 'keylock', 1);
        engine.setValue('[Channel2]', 'play', 1);
    }
    if (control === 23) {
        engine.setValue('[Channel1]', 'keylock', 1);
        engine.setValue('[Channel1]', 'play', 1);
    }
    if (control === 24) engine.setValue('[Channel2]', 'sync_enabled', 1);
    if (control === 25) engine.setValue('[Channel1]', 'sync_enabled', 1);
    if (control === 29) engine.setValue('[Library]', 'MoveDown', 1);
    if (control === 30) {
        engine.trigger('[Channel1]', 'track_loaded');
        engine.trigger('[Channel2]', 'track_loaded');
    }
};
