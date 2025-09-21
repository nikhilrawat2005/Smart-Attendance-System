// JavaScript for Smart Attendance System
document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Image preview for file inputs
    const photoInputs = document.querySelectorAll('input[type="file"]');
    photoInputs.forEach(input => {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    // Create preview image
                    const preview = document.createElement('img');
                    preview.src = e.target.result;
                    preview.className = 'preview-img mt-2';
                    preview.style.maxWidth = '100px';
                    
                    // Remove existing preview
                    const existingPreview = input.parentNode.querySelector('.preview-img');
                    if (existingPreview) {
                        existingPreview.remove();
                    }
                    
                    // Add new preview
                    input.parentNode.appendChild(preview);
                }
                reader.readAsDataURL(file);
            }
        });
    });
    
    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let valid = true;
            const requiredInputs = form.querySelectorAll('[required]');
            
            requiredInputs.forEach(input => {
                if (!input.value.trim()) {
                    valid = false;
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                }
            });
            
            if (!valid) {
                e.preventDefault();
                // Scroll to first invalid input
                const firstInvalid = form.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    });
    
    // Auto-format student ID
    const studentIdInputs = document.querySelectorAll('input[name$="_id"]');
    studentIdInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value) {
                // Convert to uppercase and remove special characters
                this.value = this.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
            }
        });
    });
    
    // Attendance table row highlighting
    const attendanceTable = document.querySelector('table');
    if (attendanceTable) {
        const rows = attendanceTable.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const radio = row.querySelector('input[type="radio"]:checked');
            if (radio && radio.value === 'present') {
                row.classList.add('table-success');
            } else if (radio && radio.value === 'absent') {
                row.classList.add('table-danger');
            }
            
            // Add event listener for status changes
            const radios = row.querySelectorAll('input[type="radio"]');
            radios.forEach(radio => {
                radio.addEventListener('change', function() {
                    rows.forEach(r => r.classList.remove('table-success', 'table-danger'));
                    
                    rows.forEach(r => {
                        const selectedRadio = r.querySelector('input[type="radio"]:checked');
                        if (selectedRadio) {
                            if (selectedRadio.value === 'present') {
                                r.classList.add('table-success');
                            } else if (selectedRadio.value === 'absent') {
                                r.classList.add('table-danger');
                            }
                        }
                    });
                });
            });
        });
    }
});