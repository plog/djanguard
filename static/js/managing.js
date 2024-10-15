//----------------------------------
// SEARCH Screens
// ---------------------------------
const majorTimezones = [
    'UTC',
    'America/New_York',
    'America/Los_Angeles',
    'Europe/London',
    'Europe/Paris',
    'Asia/Tokyo',
    'Asia/Singapore',
    'Australia/Sydney',
    'America/Chicago',
    'America/Sao_Paulo'
];

function handleAction(selector, method, confirmationMessage) {
    document.querySelectorAll(selector).forEach(button => {
        button.addEventListener('click', function() {
            const id    = this.getAttribute('data-sensor-id');
            const model = 'sensor'
            let verb = null;
            if(method == 'delete'){
                verb = method;
            }else{
                verb = 'GET';
            }
            if (confirm(confirmationMessage)) {
                $.ajax({
                    url: `/api/${model}/${method}/${id}/`,
                    method: verb,
                    headers: {'X-CSRFToken': Cookies.get('csrftoken')},         
                    success: function () {
                        alert(`Item ${id} deleted`);
                        window.location.reload();
                    },
                    error: function (error) {
                        console.error(`Failed to ${method} the item.`, error);
                        alert(`Cannot ${method} item`);
                    }                               
                })
            }
        });
    });
}

// Debounce function to prevent frequent fetch calls during typing
function debounce(func, delay) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => func.apply(this, args), delay);
    };
}

function spin(val) {
    const spinner = document.getElementById('spinner');
    const reload  = document.getElementById('reload');
    if (val == 'none') {
        setTimeout(() => { 
            spinner.style.display = 'none';
            reload.style.display = 'block';
        }, 1000);
    } else {
        spinner.style.display = 'block';
        reload.style.display  = 'none';
    }
}

// Function to populate timezone dropdown and handle changes
function setupTimezoneSelector() {
    const savedTimezone  = localStorage.getItem('selectedTimezone');   
    const timezoneSelect = document.getElementById('timezone');
    if(!timezoneSelect) return;

    majorTimezones.forEach(tz => {
        const option = document.createElement('option');
        option.value = tz;
        option.text = tz;
        timezoneSelect.appendChild(option);
        if (tz === savedTimezone) {
            option.selected = true;
        }
    });

    if (savedTimezone && majorTimezones.includes(savedTimezone)) {
        timezoneSelect.value = savedTimezone;
    } else {
        timezoneSelect.value = 'UTC';
        localStorage.setItem('selectedTimezone', 'UTC');
    }

    timezoneSelect.addEventListener('change', () => {
        localStorage.setItem('selectedTimezone', timezoneSelect.value);
        window.location.reload();
    });
}

// Function to format date based on selected timezone
function formatDate(dateString) {
    try {
        const timezone = localStorage.getItem('selectedTimezone') || 'UTC';
        const tz = moment.utc(dateString).tz(timezone);
        return tz.toDate(); // Use .toDate() if you need a Date object, otherwise return tz directly if using d3
    } catch (error) {
        return new Date(dateString); // Fallback to the original date if there's an error
    }
}

// Fetch sensor data from the server
async function fetchBackend(searchTerm, model) {
    try {
        const searchTermValue = searchTerm.value.toLowerCase();
        const response = await fetch('/api/sensor/', {method: 'GET',headers: { 'Content-Type': 'application/json', 'search': searchTermValue }});
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        console.log(data)
       displaySensors(data)
    } catch (error) {
        console.error('Error fetching sensor:', error);
    }
}

function setupSearchInput(searchInput,model){
    const reload      = document.getElementById('reload');
    if(searchInput && reload){
        searchInput.addEventListener('keyup', debounce(() => {
            spin('block');
            fetchBackend(searchInput,model);
        }, 500));
        reload.addEventListener('click', () => {
            spin('block');
            fetchBackend(searchInput,model);
        });
    }
}

// Function to dynamically insert session data into the table
function displaySensors(sensors) {
    const tableBody = document.getElementById('sensor-table').getElementsByTagName('tbody')[0];
    tableBody.innerHTML = '';  // Clear existing rows
    sensors.forEach(sensor => {
        tableBody.insertAdjacentHTML('beforeend', createSensorRow(sensor));
    });
    handleAction('.sensor-delete-btn' , 'delete' , 'Delete this sensor? THIS ACTION CANNOT BE UNDONE.');
    spin('none');
}

function onlyNumberKey(evt) {
    // Only ASCII character in that range allowed
    let ASCIICode = (evt.which) ? evt.which : evt.keyCode
    if (ASCIICode > 31 && (ASCIICode < 48 || ASCIICode > 57))
        return false;
    return true;
}

function onlyAlphaNumericKey(evt) {
    // Get the ASCII code of the key pressed
    let ASCIICode = (evt.which) ? evt.which : evt.keyCode;
    // Allow control keys like backspace (ASCII < 32)
    if (ASCIICode < 32) {
        return true;
    }
    // Allow numbers (48-57), uppercase letters (65-90), lowercase letters (97-122), dash (45), and underscore (95)
    if (
        (ASCIICode >= 48 && ASCIICode <= 57) ||    // Numbers 0-9
        (ASCIICode >= 65 && ASCIICode <= 90) ||    // Uppercase letters A-Z
        (ASCIICode >= 97 && ASCIICode <= 122) ||   // Lowercase letters a-z
        ASCIICode === 32 ||                        // Space
        ASCIICode === 45 ||                        // Hyphen (-)
        ASCIICode === 95) { // Underscore (_)
        return true;
    }
    // Otherwise, prevent the input
    return false;
}

document.addEventListener('DOMContentLoaded', function () {
    setupTimezoneSelector();
    const searchSensors = document.getElementById('search-sensor-input');
    if(searchSensors){
        setupSearchInput(searchSensors,'sensor')
        spin('block');
        fetchBackend(searchSensors,'sensor');
    }    

    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

})