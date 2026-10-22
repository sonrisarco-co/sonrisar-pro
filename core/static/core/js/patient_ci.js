(function () {
    'use strict';
    function format(value, complete) {
        // Preserve foreign documents and unexpected lengths without losing data.
        if (!/^[0-9.\-\s]*$/.test(value)) return value;
        var digits = value.replace(/\D/g, '');
        if (digits.length > 8) return value;
        if (digits.length === 8 || (complete && digits.length === 7)) {
            return digits.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, '.') + '-' + digits.slice(-1);
        }
        return digits.slice(0, 1) + (digits.length > 1 ? '.' + digits.slice(1, 4) : '') +
            (digits.length > 4 ? '.' + digits.slice(4) : '');
    }
    function update(input, complete) {
        var before = input.value;
        var cursor = input.selectionStart;
        var count = before.slice(0, cursor).replace(/\D/g, '').length;
        var after = format(before, complete);
        if (before === after) return;
        input.value = after;
        var position = 0;
        while (position < after.length && count > 0) {
            if (/\d/.test(after.charAt(position))) count--;
            position++;
        }
        if (cursor === before.length) position = after.length;
        input.setSelectionRange(position, position);
    }
    // Delegation also covers the patient modal inserted through AJAX.
    document.addEventListener('beforeinput', function (event) {
        var input = event.target;
        if (!input.matches('input[data-ci-format]')) return;
        var start = input.selectionStart, end = input.selectionEnd;
        if (start !== end) return;
        if (event.inputType === 'deleteContentBackward' && /[.\-]/.test(input.value.charAt(start - 1)) && start > 1) {
            input.setSelectionRange(start - 2, end);
        } else if (event.inputType === 'deleteContentForward' && /[.\-]/.test(input.value.charAt(start))) {
            input.setSelectionRange(start, end + 2);
        }
    });
    document.addEventListener('input', function (event) {
        if (event.target.matches('input[data-ci-format]')) update(event.target, false);
    });
    document.addEventListener('focusout', function (event) {
        if (event.target.matches('input[data-ci-format]')) update(event.target, true);
    });
    document.querySelectorAll('input[data-ci-format]').forEach(function (input) {
        update(input, true);
    });
}());
