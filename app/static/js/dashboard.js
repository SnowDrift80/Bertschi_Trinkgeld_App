// Fomantic init (run after DOM ready)
document.addEventListener('DOMContentLoaded', () => {
  $('.ui.dropdown').dropdown();
  $('.ui.checkbox').checkbox();

  // ---- Delete modal (dashboard)
  document.querySelectorAll('.show-header-delete-modal').forEach(btn => {
    btn.addEventListener('click', function () {
      const url = this.getAttribute('data-delete-url');
      const form = document.getElementById('deleteHeaderFormDashboard');
      if (form) {
        form.action = url;
        $('#deleteHeaderModalDashboard').modal('show');
      }
    });
  });

  // ---- Standort-required guard
  function currentLocationValue() {
    return $('select[name="location"]').val();
  }
  $(document).on('click', 'a.requires-location, button.requires-location', function (e) {
    if (!currentLocationValue()) {
      e.preventDefault();
      $('#locationRequiredModal').modal('show');
      return false;
    }
  });

  // ---- Visual disable for "Erstellen" button
  (function () {
    const $dropdown = $('select[name="location"]');
    const $createButton = $('#createButton');
    if ($dropdown.length && $createButton.length) {
      function updateButtonState() {
        const hasSelection = !!$dropdown.val();
        $createButton.toggleClass('disabled', !hasSelection);
      }
      updateButtonState();
      $dropdown.on('change', updateButtonState);
    }
  })();

  // ---- Export modal logic (superadmin only)
  if (window.IS_SUPERADMIN && document.getElementById('exportModal')) {
    function rebuildUserDropdown(users, headerText) {
      const $dd = $('#export-user-dropdown');
      const $menu = $dd.find('.menu');
      $menu.empty();

      if (headerText) $menu.append(`<div class="header">${headerText}</div>`);

      if (!users.length) {
        $menu.append('<div class="item disabled">Keine Benutzer gefunden</div>');
      } else {
        users.forEach(u => {
          const label = `${u.name} (${u.username}) — ${u.location}`;
          $menu.append(`<div class="item" data-value="${u.id}">${label}</div>`);
        });
      }

      $dd.dropdown('clear').dropdown('refresh');
    }

    async function refreshUsersForExport() {
      const allChecked = $('#all_locations').is(':checked');
      const loc = $('#location_dropdown').val() || '';
      const params = new URLSearchParams();
      params.set('all', allChecked ? '1' : '0');
      if (!allChecked && loc) params.set('location', loc);

      try {
        const resp = await fetch(`/api/users-for-export?${params.toString()}`, { credentials: 'same-origin' });
        const users = await resp.json();
        const header = allChecked ? 'Alle Standorte' : (loc ? `Standort: ${loc}` : 'Benutzer');
        rebuildUserDropdown(users, header);
      } catch (e) {
        rebuildUserDropdown([], 'Fehler beim Laden');
        console.error(e);
      }
    }

    $('#all_locations').on('change', function () {
      const checked = $(this).is(':checked');
      if (checked) $('#location_dropdown').val('').dropdown('clear');
      refreshUsersForExport();
    });

    $('#location_dropdown').on('change', function () {
      const val = $(this).val();
      if (val) $('#all_locations').prop('checked', false).closest('.ui.checkbox').checkbox('set unchecked');
      refreshUsersForExport();
    });

    $('#exportModal').modal({
      onShow: function () {
        $('#all_locations').prop('checked', true).closest('.ui.checkbox').checkbox('set checked');
        $('#location_dropdown').val('').dropdown('clear');

        $('#export-user-dropdown').dropdown({
          clearable: true,
          fullTextSearch: 'exact',
          forceSelection: false,
          selectOnKeydown: false
        });

        refreshUsersForExport();
      }
    });
  }
});


// === Dashboard Export Date Presets ===

(function () {
  const $from = $('input[name="date_from"]');
  const $to   = $('input[name="date_to"]');

  function ymd(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }
  function setRange(startDate, endDate) {
    $from.val(ymd(startDate));
    $to.val(ymd(endDate));
  }
  function startOfToday() {
    const d = new Date();
    d.setHours(0,0,0,0);
    return d;
  }
  function addDays(d, n) {
    const x = new Date(d);
    x.setDate(x.getDate() + n);
    return x;
  }

  // Monday-based week helpers (Europe/Zurich typical)
  function startOfISOWeek(d) {
    const x = new Date(d);
    x.setHours(0,0,0,0);
    // getDay(): 0=Sun..6=Sat → convert to ISO Mon=0..Sun=6
    const iso = (x.getDay() + 6) % 7;
    return addDays(x, -iso);
  }

  function lastWeekRange(today) {
    const thisWeekStart = startOfISOWeek(today);
    const lastWeekStart = addDays(thisWeekStart, -7);
    const lastWeekEnd   = addDays(lastWeekStart, 6);
    return [lastWeekStart, lastWeekEnd];
  }

  function monthToDateRange(today) {
    const start = new Date(today.getFullYear(), today.getMonth(), 1);
    return [start, today];
  }

  function lastMonthRange(today) {
    const y = today.getFullYear();
    const m = today.getMonth(); // 0..11
    const start = new Date(y, m - 1, 1);
    const end   = new Date(y, m, 0); // day 0 = last day of prev month
    return [start, end];
  }

  function lastQuarterRange(today) {
    const y = today.getFullYear();
    const m = today.getMonth(); // 0..11
    const curQ = Math.floor(m / 3); // 0..3
    const prevQ = (curQ + 3) % 4;
    const yearAdj = curQ === 0 ? y - 1 : y;
    const startMonth = prevQ * 3;
    const start = new Date(yearAdj, startMonth, 1);
    const end   = new Date(yearAdj, startMonth + 3, 0); // day 0 of next q = last day of prev q
    return [start, end];
  }

  function yearToDateRange(today) {
    const start = new Date(today.getFullYear(), 0, 1);
    return [start, today];
  }

  $(document).on('click', '#export-date-presets button[data-preset]', function () {
    const preset = $(this).data('preset');
    const today = startOfToday();

    switch (preset) {
      case 'today': {
        setRange(today, today);
        break;
      }
      case 'last-week': {
        const [s, e] = lastWeekRange(today);
        setRange(s, e);
        break;
      }
      case 'mtd': {
        const [s, e] = monthToDateRange(today);
        setRange(s, e);
        break;
      }
      case 'last-month': {
        const [s, e] = lastMonthRange(today);
        setRange(s, e);
        break;
      }
      case 'last-quarter': {
        const [s, e] = lastQuarterRange(today);
        setRange(s, e);
        break;
      }
      case 'ytd': {
        const [s, e] = yearToDateRange(today);
        setRange(s, e);
        break;
      }
    }
  });


})();
