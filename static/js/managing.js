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

function onlyNumberKey(evt) {
    // Only ASCII character in that range allowed
    let ASCIICode = (evt.which) ? evt.which : evt.keyCode
    if (ASCIICode > 31 && (ASCIICode < 48 || ASCIICode > 57))
        return false;
    return true;
}

function isUrlValid(string) {
    try {
      new URL(string);
      return true;
    } catch (err) {
      return false;
    }
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

async function testAction(actionId, callback) {
    $.ajax({
        url    : `/api/action/${actionId}/run/`,
        type   : 'POST',
        headers: {'X-CSRFToken': Cookies.get('csrftoken')},
        success: function(response) {
            let action_results = {
                response : JSON.stringify(response),
                img      : "/static/img/fail.png",
                message  : response.body
            }
            if(response.expected_value === response.actual_value || response.actual_value == 'pass'){
                action_results.img = "/static/img/pass.png";
            }else{
                action_results.img = "/static/img/fail.png";
            }
            callback(action_results);
        },
        error: function(xhr, status, error) {
            callback({
                response : xhr.responseJSON.error,
                message  : "Error calling the test:" + xhr.responseJSON.details,
                img: "/static/img/fail.png"
            }); 
        }
    });
}

document.addEventListener('DOMContentLoaded', function () {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    setupTimezoneSelector();
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        console.log('DARK')
    }     
})