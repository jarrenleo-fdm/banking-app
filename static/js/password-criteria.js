(function () {
  var CRITERIA = [
    {
      id: "pc-length",
      label: "At least 8 characters",
      test: function (p) {
        return p.length >= 8;
      },
    },
    {
      id: "pc-upper",
      label: "One uppercase letter (A–Z)",
      test: function (p) {
        return /[A-Z]/.test(p);
      },
    },
    {
      id: "pc-lower",
      label: "One lowercase letter (a–z)",
      test: function (p) {
        return /[a-z]/.test(p);
      },
    },
    {
      id: "pc-digit",
      label: "One digit (0–9)",
      test: function (p) {
        return /\d/.test(p);
      },
    },
    {
      id: "pc-special",
      label: "One special character",
      test: function (p) {
        return /[^A-Za-z0-9]/.test(p);
      },
    },
  ];

  function buildChecklist() {
    var ul = document.createElement("ul");
    ul.className = "password-criteria";
    CRITERIA.forEach(function (c) {
      var li = document.createElement("li");
      li.id = c.id;
      li.textContent = c.label;
      ul.appendChild(li);
    });
    return ul;
  }

  function update(password) {
    CRITERIA.forEach(function (c) {
      var li = document.getElementById(c.id);
      if (li) li.classList.toggle("met", c.test(password));
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    // Matches id_password1 (registration) and id_new_password1 (password reset)
    var fields = document.querySelectorAll(
      "input[type='password'][id$='password1']",
    );
    fields.forEach(function (field) {
      var checklist = buildChecklist();
      field.parentNode.insertBefore(checklist, field.nextSibling);
      field.addEventListener("input", function () {
        update(field.value);
      });
      field.addEventListener("change", function () {
        update(field.value);
      });
    });
  });
})();
