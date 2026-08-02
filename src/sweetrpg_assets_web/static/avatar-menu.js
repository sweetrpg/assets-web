/* Avatar dropdown menu behavior, shared by main-web and catalog-web - see the
 * suite-avatar-menu OpenSpec change in sweetrpg/platform. Each consuming frontend renders its
 * own markup (Askama, Leaf) around the shared `.avatar-menu` / `.avatar-menu-trigger` /
 * `.avatar-menu-panel` / `.avatar-menu-item` class contract; this file only owns
 * open/close/focus behavior, matching main-web's existing theme.js style (plain DOM APIs, no
 * build step).
 */
(function () {
  function closeMenu(panel, trigger) {
    panel.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
  }

  function openMenu(panel, trigger) {
    panel.hidden = false;
    trigger.setAttribute('aria-expanded', 'true');
  }

  function initMenu(menu) {
    const trigger = menu.querySelector('.avatar-menu-trigger');
    const panel = menu.querySelector('.avatar-menu-panel');
    if (!trigger || !panel) {
      return;
    }

    trigger.setAttribute('aria-haspopup', 'true');
    trigger.setAttribute('aria-expanded', 'false');
    closeMenu(panel, trigger);

    trigger.addEventListener('click', function (event) {
      event.stopPropagation();
      if (panel.hidden) {
        openMenu(panel, trigger);
      } else {
        closeMenu(panel, trigger);
      }
    });

    panel.addEventListener('click', function (event) {
      const item = event.target.closest('.avatar-menu-item');
      if (item) {
        closeMenu(panel, trigger);
      }
    });

    document.addEventListener('click', function (event) {
      if (!panel.hidden && !menu.contains(event.target)) {
        closeMenu(panel, trigger);
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !panel.hidden) {
        closeMenu(panel, trigger);
        trigger.focus();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.avatar-menu').forEach(initMenu);
  });
})();
