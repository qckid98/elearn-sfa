// Fashion School - App JavaScript

document.addEventListener('DOMContentLoaded', function () {
  // Mobile sidebar toggle
  const mobileToggle = document.querySelector('.mobile-toggle');
  const sidebar = document.querySelector('.sidebar');
  const sidebarOverlay = document.querySelector('.sidebar-overlay');

  if (mobileToggle) {
    mobileToggle.addEventListener('click', function () {
      sidebar.classList.toggle('open');
      sidebarOverlay.classList.toggle('show');
    });
  }

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', function () {
      sidebar.classList.remove('open');
      sidebarOverlay.classList.remove('show');
    });
  }

  // Sidebar toggle (collapse)
  const sidebarToggle = document.querySelector('.sidebar-toggle');
  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('collapsed');
      document.querySelector('.main-content').classList.toggle('expanded');
    });
  }

  // Dropdown menus
  const dropdowns = document.querySelectorAll('.dropdown');
  dropdowns.forEach(function (dropdown) {
    const trigger = dropdown.querySelector('[data-dropdown-toggle]');
    const menu = dropdown.querySelector('.dropdown-menu');

    if (trigger && menu) {
      trigger.addEventListener('click', function (e) {
        e.stopPropagation();
        menu.classList.toggle('show');
      });
    }
  });

  // Close dropdowns when clicking outside
  document.addEventListener('click', function () {
    document.querySelectorAll('.dropdown-menu.show').forEach(function (menu) {
      menu.classList.remove('show');
    });
  });

  // Auto-dismiss alerts
  const alerts = document.querySelectorAll('.alert[data-auto-dismiss]');
  alerts.forEach(function (alert) {
    const timeout = parseInt(alert.dataset.autoDismiss) || 5000;
    setTimeout(function () {
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-10px)';
      setTimeout(function () {
        alert.remove();
      }, 300);
    }, timeout);
  });

  // Active nav item
  const currentPath = window.location.pathname;
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(function (item) {
    const href = item.getAttribute('href');
    if (href && currentPath.includes(href) && href !== '/') {
      item.classList.add('active');
    } else if (href === '/' && currentPath === '/') {
      item.classList.add('active');
    }
  });

  // Form validation feedback
  const forms = document.querySelectorAll('form[data-validate]');
  forms.forEach(function (form) {
    form.addEventListener('submit', function (e) {
      const inputs = form.querySelectorAll('[required]');
      let isValid = true;

      inputs.forEach(function (input) {
        if (!input.value.trim()) {
          isValid = false;
          input.classList.add('is-invalid');
        } else {
          input.classList.remove('is-invalid');
        }
      });

      if (!isValid) {
        e.preventDefault();
      }
    });
  });

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });

  // Initialize tooltips (if any)
  const tooltips = document.querySelectorAll('[data-tooltip]');
  tooltips.forEach(function (el) {
    el.addEventListener('mouseenter', function () {
      const text = this.dataset.tooltip;
      const tooltip = document.createElement('div');
      tooltip.className = 'tooltip';
      tooltip.textContent = text;
      document.body.appendChild(tooltip);

      const rect = this.getBoundingClientRect();
      tooltip.style.top = (rect.top - tooltip.offsetHeight - 8) + 'px';
      tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
    });

    el.addEventListener('mouseleave', function () {
      const tooltip = document.querySelector('.tooltip');
      if (tooltip) {
        tooltip.remove();
      }
    });
  });

  // Global Delete Confirmation
  document.body.addEventListener('submit', function (e) {
    if (e.target.classList.contains('delete-form')) {
      e.preventDefault();
      const form = e.target;
      const message = form.dataset.confirm || 'Yakin ingin menghapus?';

      confirmAction(message).then(function (result) {
        if (result) {
          form.submit();
        }
      });
    }
  });
});

// Utility functions
function formatNumber(num) {
  return new Intl.NumberFormat('id-ID').format(num);
}

function formatDate(date) {
  return new Intl.DateTimeFormat('id-ID', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }).format(new Date(date));
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'times-circle' : 'info-circle'}"></i>
    <span>${message}</span>
  `;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('show');
  }, 100);

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function confirmAction(message) {
  return new Promise((resolve) => {
    const modal = document.createElement('div');
    modal.className = 'confirm-modal';
    modal.innerHTML = `
      <div class="confirm-modal-content">
        <div class="confirm-modal-icon">
          <i class="fas fa-question-circle"></i>
        </div>
        <p>${message}</p>
        <div class="confirm-modal-actions">
          <button class="btn btn-secondary" data-action="cancel">Batal</button>
          <button class="btn btn-primary" data-action="confirm">Ya, Lanjutkan</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('[data-action="cancel"]').addEventListener('click', () => {
      modal.remove();
      resolve(false);
    });

    modal.querySelector('[data-action="confirm"]').addEventListener('click', () => {
      modal.remove();
      resolve(true);
    });
  });
}
