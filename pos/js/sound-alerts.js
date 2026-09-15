window.CofiSoundAlerts = (() => {
    let audioContext = null;
    let unlocked = false;

    function getAudioContext() {
        if (audioContext) {
            return audioContext;
        }

        const AudioContextClass =
            window.AudioContext
            || window.webkitAudioContext;

        if (!AudioContextClass) {
            return null;
        }

        try {
            audioContext =
                new AudioContextClass();

            return audioContext;

        } catch {
            return null;
        }
    }

    async function unlockAudio() {
        if (unlocked) {
            return true;
        }

        const context =
            getAudioContext();

        if (!context) {
            return false;
        }

        try {
            if (
                context.state === "suspended"
            ) {
                await context.resume();
            }

            unlocked =
                context.state === "running";

            return unlocked;

        } catch {
            return false;
        }
    }

    function schedulePattern(notes) {
        const context =
            getAudioContext();

        if (
            !context
            || !unlocked
        ) {
            return false;
        }

        const schedule = () => {
            const baseTime =
                context.currentTime + 0.02;

            notes.forEach(note => {
                const oscillator =
                    context.createOscillator();

                const gain =
                    context.createGain();

                const start =
                    baseTime + note.offset;

                const end =
                    start + note.duration;

                oscillator.type =
                    note.type || "sine";

                oscillator.frequency
                    .setValueAtTime(
                        note.frequency,
                        start
                    );

                gain.gain
                    .setValueAtTime(
                        0.0001,
                        start
                    );

                gain.gain
                    .exponentialRampToValueAtTime(
                        note.volume || 0.15,
                        start + 0.015
                    );

                gain.gain
                    .exponentialRampToValueAtTime(
                        0.0001,
                        end
                    );

                oscillator.connect(gain);
                gain.connect(
                    context.destination
                );

                oscillator.start(start);
                oscillator.stop(
                    end + 0.02
                );
            });
        };

        if (
            context.state === "suspended"
        ) {
            context.resume()
                .then(() => {
                    if (
                        context.state
                        === "running"
                    ) {
                        schedule();
                    }
                })
                .catch(() => {});

            return true;
        }

        if (
            context.state !== "running"
        ) {
            return false;
        }

        schedule();

        return true;
    }

    function playNewOrder() {
        return schedulePattern([
            {
                frequency: 880,
                offset: 0,
                duration: 0.13,
                volume: 0.16,
            },
            {
                frequency: 1175,
                offset: 0.16,
                duration: 0.2,
                volume: 0.18,
            },
        ]);
    }

    function playOrderReady() {
        return schedulePattern([
            {
                frequency: 659,
                offset: 0,
                duration: 0.1,
                volume: 0.13,
            },
            {
                frequency: 784,
                offset: 0.12,
                duration: 0.1,
                volume: 0.14,
            },
            {
                frequency: 988,
                offset: 0.24,
                duration: 0.22,
                volume: 0.16,
            },
        ]);
    }

    [
        "pointerdown",
        "touchstart",
    ].forEach(eventName => {
        window.addEventListener(
            eventName,
            unlockAudio,
            {
                passive: true,
            }
        );
    });

    return {
        unlockAudio,
        playNewOrder,
        playOrderReady,
    };
})();
