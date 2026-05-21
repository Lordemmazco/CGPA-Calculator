document.addEventListener('DOMContentLoaded', () => {
    const courseList = document.getElementById('course-list');
    const generateCoursesBtn = document.getElementById('generate-courses-btn');
    const numCoursesInput = document.getElementById('num-courses');
    const clearBtn = document.getElementById('clear-btn');
    const calculateBtn = document.getElementById('calculate-btn');
    
    // Result Reveal Elements
    const quoteOverlay = document.getElementById('quote-overlay');
    const performanceQuote = document.getElementById('performance-quote');
    const revealBtn = document.getElementById('reveal-btn');
    
    const resultOverlay = document.getElementById('result-overlay');
    const cgpaDisplay = document.getElementById('cgpa-display');
    const classificationDisplay = document.getElementById('classification-display');
    const totalUnitsDisplay = document.getElementById('total-units-display');
    const closeResultBtn = document.getElementById('close-result-btn');
    const template = document.getElementById('course-row-template');
    
    // History Panel Elements
    const historyToggleBtn = document.getElementById('history-toggle-btn');
    const historyPanel = document.getElementById('history-panel');
    const historyBackdrop = document.getElementById('history-backdrop');
    const historyCloseBtn = document.getElementById('history-close-btn');

    let currentCGPA = null;
    let currentTotalUnits = null;
    let editingHistoryId = null; // Track if we are editing an existing history

    function addCourseRow() {
        if (!template) return;
        const clone = template.content.cloneNode(true);
        
        const row = clone.querySelector('.course-row');
        courseList.appendChild(clone);
        if (typeof lucide !== 'undefined') {
            lucide.createIcons({ root: row });
        }

        const removeBtn = row.querySelector('.btn-remove');
        removeBtn.addEventListener('click', () => {
            row.remove();
        });
    }

    function generateCourses() {
        if (!courseList) return;
        courseList.innerHTML = '';
        const count = parseInt(numCoursesInput.value);
        if (isNaN(count) || count < 1) {
            alert("Please enter a valid number of courses (at least 1).");
            return;
        }
        for (let i = 0; i < count; i++) {
            addCourseRow();
        }
    }

    // Initial generation
    if (courseList) {
        generateCourses();
    }

    if (generateCoursesBtn) {
        generateCoursesBtn.addEventListener('click', generateCourses);
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            generateCourses(); // Reset to whatever number is in the input
        });
    }

    function getQuote(cgpa) {
        if (cgpa >= 4.5) return "“Excellence is not an act, but a habit.” – Aristotle";
        if (cgpa >= 3.5) return "“Success is the sum of small efforts, repeated day-in and day-out.” – Robert Collier";
        if (cgpa >= 2.5) return "“It does not matter how slowly you go as long as you do not stop.” – Confucius";
        return "“Our greatest weakness lies in giving up. The most certain way to succeed is always to try just one more time.” – Thomas Edison";
    }

    function getClassification(cgpa) {
        if (cgpa >= 4.5) return "First Class Honours";
        if (cgpa >= 3.5) return "Second Class Honours (Upper)";
        if (cgpa >= 2.4) return "Second Class Honours (Lower)";
        if (cgpa >= 1.5) return "Third Class Honours";
        if (cgpa >= 1.0) return "Pass";
        return "Fail";
    }

    function autoSave(cgpa, units, courses) {
        const url = editingHistoryId ? `/edit_history/${editingHistoryId}` : '/save_cgpa';
        
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                cgpa: cgpa,
                units: units,
                courses: courses
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(editingHistoryId ? 'History updated!' : 'CGPA auto-saved!');
                // Reset edit state after successful update
                if (editingHistoryId) {
                    editingHistoryId = null;
                    if (calculateBtn) calculateBtn.textContent = 'Calculate CGPA';
                }
            }
        })
        .catch(error => console.error('Error saving:', error));
    }

    if (calculateBtn) {
        calculateBtn.addEventListener('click', () => {
            let totalUnits = 0;
            let totalPoints = 0;
            let valid = true;

            const rows = document.querySelectorAll('.course-row');
            
            if (rows.length === 0) {
                alert("Please add at least one course.");
                return;
            }

            const coursesData = [];

            rows.forEach(row => {
                const nameInput = row.querySelector('.course-name').value;
                const unitsInput = row.querySelector('.course-units').value;
                const gradeSelect = row.querySelector('.course-grade').value;

                if (unitsInput && gradeSelect !== "") {
                    const units = parseFloat(unitsInput);
                    const gradePoint = parseFloat(gradeSelect);

                    if (units > 0) {
                        totalUnits += units;
                        totalPoints += (units * gradePoint);
                        coursesData.push({
                            name: nameInput,
                            units: units,
                            grade: gradeSelect
                        });
                    } else {
                        valid = false;
                        alert("Units must be greater than 0 for all entered courses.");
                    }
                }
            });

            if (!valid) return;

            if (totalUnits === 0) {
                alert("Please fill in units and grades to calculate CGPA.");
                return;
            }

            const cgpa = totalPoints / totalUnits;
            
            currentCGPA = cgpa;
            currentTotalUnits = totalUnits;
            
            cgpaDisplay.textContent = cgpa.toFixed(2);
            classificationDisplay.textContent = getClassification(cgpa);
            totalUnitsDisplay.textContent = `Total Units: ${totalUnits}`;
            
            performanceQuote.textContent = getQuote(cgpa);
            
            quoteOverlay.style.display = 'flex';
            
            // Auto-save or Update result
            autoSave(cgpa, totalUnits, coursesData);
        });
    }
    
    if (revealBtn) {
        revealBtn.addEventListener('click', () => {
            quoteOverlay.style.display = 'none';
            resultOverlay.style.display = 'flex';
        });
    }

    if (closeResultBtn) {
        closeResultBtn.addEventListener('click', () => {
            resultOverlay.style.display = 'none';
            location.reload(); // Reload to show updated history
        });
    }

    // History Panel Logic
    function toggleHistory() {
        if (historyPanel.classList.contains('open')) {
            historyPanel.classList.remove('open');
            historyBackdrop.style.display = 'none';
        } else {
            historyPanel.classList.add('open');
            historyBackdrop.style.display = 'block';
        }
    }

    if (historyToggleBtn) {
        historyToggleBtn.addEventListener('click', toggleHistory);
    }
    if (historyCloseBtn) {
        historyCloseBtn.addEventListener('click', toggleHistory);
    }
    if (historyBackdrop) {
        historyBackdrop.addEventListener('click', toggleHistory);
    }

    // ── Edit History Flow ───────────────────────────
    window.restoreHistory = function(btnElement, id) {
        const coursesRaw = btnElement.dataset.courses;
        if (!coursesRaw || coursesRaw === 'null') {
            alert('No course details were saved for this record (old record format).');
            return;
        }

        try {
            const courses = JSON.parse(coursesRaw);
            
            // Clear current inputs
            if (courseList) courseList.innerHTML = '';
            
            // Populate rows
            courses.forEach(course => {
                addCourseRow();
                const lastRow = courseList.lastElementChild;
                lastRow.querySelector('.course-name').value = course.name || '';
                lastRow.querySelector('.course-units').value = course.units || '';
                lastRow.querySelector('.course-grade').value = course.grade || '';
            });

            // Set edit state
            editingHistoryId = id;
            if (calculateBtn) calculateBtn.textContent = 'Update Result';
            
            // Close history panel
            toggleHistory();
            
            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
            
        } catch (e) {
            console.error('Failed to parse course data', e);
            alert('Failed to load courses.');
        }
    };
});
