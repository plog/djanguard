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
    });
}

// Function to format date based on selected timezone
function formatDate(dateString) {
    try {
        const timezone = localStorage.getItem('selectedTimezone');
        const date = moment.utc(dateString);
        return moment.utc(date).tz(timezone).format('MM/DD HH:mm z');
    } catch (error) {
        return '';
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