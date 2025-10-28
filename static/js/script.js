// Initialize Lucide icons
console.log('Script.js loaded successfully!');
lucide.createIcons();

// Theme toggle functionality
console.log('Initializing theme toggle...');

const themeToggle = document.getElementById('theme-toggle');
const themeToggleMobile = document.getElementById('theme-toggle-mobile');
const themeIcon = document.getElementById('theme-icon');
const themeIconMobile = document.getElementById('theme-icon-mobile');
const html = document.documentElement;

console.log('Theme toggle elements found:', {
    themeToggle: !!themeToggle,
    themeToggleMobile: !!themeToggleMobile,
    themeIcon: !!themeIcon,
    themeIconMobile: !!themeIconMobile
});

// Check for saved theme preference or default to dark
const currentTheme = localStorage.getItem('theme') || 'dark';
html.classList.add(currentTheme);

// Set initial icons
if (currentTheme === 'light') {
    themeIcon.setAttribute('data-lucide', 'moon');
    themeIconMobile.setAttribute('data-lucide', 'moon');
} else {
    themeIcon.setAttribute('data-lucide', 'sun');
    themeIconMobile.setAttribute('data-lucide', 'sun');
}

// Reinitialize icons after setting the initial icon
lucide.createIcons();

// Function to toggle theme
function toggleTheme() {
    const isDark = html.classList.contains('dark');
    console.log('Current theme:', isDark ? 'dark' : 'light');
    
    if (isDark) {
        html.classList.remove('dark');
        html.classList.add('light');
        themeIcon.setAttribute('data-lucide', 'moon');
        themeIconMobile.setAttribute('data-lucide', 'moon');
        localStorage.setItem('theme', 'light');
        console.log('Switched to light theme');
    } else {
        html.classList.remove('light');
        html.classList.add('dark');
        themeIcon.setAttribute('data-lucide', 'sun');
        themeIconMobile.setAttribute('data-lucide', 'sun');
        localStorage.setItem('theme', 'dark');
        console.log('Switched to dark theme');
    }
    
    // Reinitialize icons after changing
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

// Make toggleTheme available globally
window.toggleTheme = toggleTheme;

// Theme toggle event listeners
if (themeToggle) {
    themeToggle.addEventListener('click', function(e) {
        console.log('Desktop theme toggle clicked!');
        e.preventDefault();
        toggleTheme();
    });
    console.log('Desktop theme toggle initialized');
} else {
    console.error('Desktop theme toggle not found!');
}

if (themeToggleMobile) {
    themeToggleMobile.addEventListener('click', function(e) {
        console.log('Mobile theme toggle clicked!');
        e.preventDefault();
        toggleTheme();
    });
    console.log('Mobile theme toggle initialized');
} else {
    console.error('Mobile theme toggle not found!');
}

// Ensure theme is properly set on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Page loaded, current theme:', localStorage.getItem('theme') || 'dark');
    console.log('HTML classes:', html.className);
});

// User dropdown menu functionality
function toggleUserMenu() {
    const dropdown = document.getElementById('user-dropdown');
    const button = document.getElementById('user-menu');
    const chevron = button.querySelector('i[data-lucide="chevron-down"]');
    
    if (dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        button.setAttribute('aria-expanded', 'true');
        if (chevron) {
            chevron.setAttribute('data-lucide', 'chevron-up');
            lucide.createIcons();
        }
    } else {
        dropdown.classList.add('hidden');
        button.setAttribute('aria-expanded', 'false');
        if (chevron) {
            chevron.setAttribute('data-lucide', 'chevron-down');
            lucide.createIcons();
        }
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('user-dropdown');
    const button = document.getElementById('user-menu');
    
    if (dropdown && !dropdown.contains(event.target) && !button.contains(event.target)) {
        dropdown.classList.add('hidden');
        button.setAttribute('aria-expanded', 'false');
        const chevron = button.querySelector('i[data-lucide="chevron-up"]');
        if (chevron) {
            chevron.setAttribute('data-lucide', 'chevron-down');
            lucide.createIcons();
        }
    }
});

// Make toggleUserMenu available globally
window.toggleUserMenu = toggleUserMenu;

// Help dropdown functionality
function toggleHelpMenu() {
    console.log('toggleHelpMenu called');
    const dropdown = document.getElementById('help-dropdown');
    
    if (dropdown) {
        if (dropdown.style.display === 'none') {
            console.log('Showing dropdown');
            dropdown.style.display = 'block';
        } else {
            console.log('Hiding dropdown');
            dropdown.style.display = 'none';
        }
    } else {
        console.log('Dropdown element not found!');
    }
}

// Close Help dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('help-dropdown');
    const button = document.getElementById('help-btn');
    
    if (dropdown && !dropdown.contains(event.target) && !button.contains(event.target)) {
        dropdown.classList.add('hidden');
        button.setAttribute('aria-expanded', 'false');
    }
});

// Make toggleHelpMenu available globally
window.toggleHelpMenu = toggleHelpMenu;

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('help-dropdown');
    const button = document.getElementById('help-btn');
    
    if (dropdown && !dropdown.contains(event.target) && !button.contains(event.target)) {
        dropdown.style.display = 'none';
    }
    
    // Close notification dropdown when clicking outside
    const notificationDropdown = document.getElementById('notification-dropdown');
    const notificationButton = event.target.closest('[onclick*="notification-dropdown"]');
    
    if (notificationDropdown && !notificationDropdown.contains(event.target) && !notificationButton) {
        notificationDropdown.classList.add('hidden');
    }
});


// Mobile menu toggle
const mobileMenuButton = document.querySelector('[aria-controls="mobile-menu"]');
const mobileMenu = document.getElementById('mobile-menu');

mobileMenuButton.addEventListener('click', () => {
    const expanded = mobileMenuButton.getAttribute('aria-expanded') === 'true';
    mobileMenuButton.setAttribute('aria-expanded', !expanded);
    mobileMenu.classList.toggle('hidden');
    
    // Toggle icons
    const menuIcon = mobileMenuButton.querySelector('[data-lucide="menu"]');
    const xIcon = mobileMenuButton.querySelector('[data-lucide="x"]');
    menuIcon.classList.toggle('hidden');
    xIcon.classList.toggle('hidden');
});

// Create modals dynamically
function createModals() {
    // Handover Signing Modal
    const signingModal = document.createElement('div');
    signingModal.id = 'signing-modal';
    signingModal.className = 'hidden fixed inset-0 overflow-y-auto z-50';
    signingModal.innerHTML = `
        <div class="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div class="fixed inset-0 transition-opacity" aria-hidden="true">
                <div class="absolute inset-0 bg-slate-900 opacity-75"></div>
            </div>
            <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div class="inline-block align-bottom bg-slate-800 rounded-xl text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-3xl sm:w-full">
                <div class="px-6 py-5 border-b border-slate-700">
                    <h3 class="text-lg leading-6 font-medium text-white">Sign Handover Document</h3>
                    <p class="mt-1 text-sm text-slate-400">Please sign below to acknowledge receipt of the assets</p>
                </div>
                <div class="px-6 py-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <h4 class="text-sm font-medium text-slate-300 mb-2">Employee Signature</h4>
                            <div class="signature-pad h-48 w-full" id="employee-signature"></div>
                            <div class="mt-2 flex justify-between">
                                <button id="clear-employee" class="text-sm text-slate-400 hover:text-slate-200">
                                    <i data-lucide="trash-2" class="h-4 w-4 inline mr-1"></i> Clear
                                </button>
                                <button id="undo-employee" class="text-sm text-slate-400 hover:text-slate-200">
                                    <i data-lucide="rotate-ccw" class="h-4 w-4 inline mr-1"></i> Undo
                                </button>
                            </div>
                            <div class="mt-4">
                                <label class="inline-flex items-center">
                                    <input type="checkbox" class="form-checkbox h-4 w-4 text-blue-600 border-slate-700 rounded focus:ring-blue-500 bg-slate-700">
                                    <span class="ml-2 text-sm text-slate-400">I acknowledge receipt of these assets</span>
                                </label>
                            </div>
                        </div>
                        <div>
                            <h4 class="text-sm font-medium text-slate-300 mb-2">IT Representative Signature</h4>
                            <div class="signature-pad h-48 w-full" id="it-signature"></div>
                            <div class="mt-2 flex justify-between">
                                <button id="clear-it" class="text-sm text-slate-400 hover:text-slate-200">
                                    <i data-lucide="trash-2" class="h-4 w-4 inline mr-1"></i> Clear
                                </button>
                                <button id="undo-it" class="text-sm text-slate-400 hover:text-slate-200">
                                    <i data-lucide="rotate-ccw" class="h-4 w-4 inline mr-1"></i> Undo
                                </button>
                            </div>
                            <div class="mt-4">
                                <div class="text-sm text-slate-400">
                                    <i data-lucide="info" class="h-4 w-4 inline mr-1 text-blue-400"></i>
                                    Sign as the IT representative verifying this handover
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="mt-6">
                        <h4 class="text-sm font-medium text-slate-300 mb-2">Handover Summary</h4>
                        <div class="bg-slate-900/50 rounded-lg p-4">
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <p class="text-xs text-slate-400">Employee</p>
                                    <p class="text-sm text-white">Sarah Johnson</p>
                                </div>
                                <div>
                                    <p class="text-xs text-slate-400">Department</p>
                                    <p class="text-sm text-white">Marketing</p>
                                </div>
                                <div>
                                    <p class="text-xs text-slate-400">Date</p>
                                    <p class="text-sm text-white">June 15, 2023</p>
                                </div>
                                <div>
                                    <p class="text-xs text-slate-400">Handover ID</p>
                                    <p class="text-sm text-white">HOV-2023-0065</p>
                                </div>
                            </div>
                            <div class="mt-4">
                                <p class="text-xs text-slate-400">Assets</p>
                                <ul class="mt-1 space-y-1">
                                    <li class="text-sm text-white flex items-center">
                                        <i data-lucide="laptop" class="h-4 w-4 mr-2 text-blue-400"></i>
                                        MacBook Pro (Serial: C02XV0ABCDEF)
                                    </li>
                                    <li class="text-sm text-white flex items-center">
                                        <i data-lucide="smartphone" class="h-4 w-4 mr-2 text-purple-400"></i>
                                        iPhone 13 (Serial: G6ABCDEF1234)
                                    </li>
                                    <li class="text-sm text-white flex items-center">
                                        <i data-lucide="mouse" class="h-4 w-4 mr-2 text-green-400"></i>
                                        Magic Mouse (Serial: MMBH2ABCDEF)
                                    </li>
                                </ul>
                            </div>
                            <div class="mt-4 flex justify-center">
                                <div id="qr-code"></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="px-6 py-4 border-t border-slate-700 flex justify-end">
                    <button type="button" class="mr-3 inline-flex justify-center px-4 py-2 border border-slate-700 shadow-sm text-sm font-medium rounded-md text-white bg-slate-700 hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500" data-close-modal="signing-modal">
                        Cancel
                    </button>
                    <button type="button" class="inline-flex justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                        Save Signatures
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(signingModal);

    // Welcome Pack Modal
    const welcomeModal = document.createElement('div');
    welcomeModal.id = 'welcome-modal';
    welcomeModal.className = 'hidden fixed inset-0 overflow-y-auto z-50';
    welcomeModal.innerHTML = `
        <div class="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div class="fixed inset-0 transition-opacity" aria-hidden="true">
                <div class="absolute inset-0 bg-slate-900 opacity-75"></div>
            </div>
            <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div class="inline-block align-bottom bg-slate-800 rounded-xl text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
                <div class="px-6 py-5 border-b border-slate-700">
                    <h3 class="text-lg leading-6 font-medium text-white">Create Welcome Pack</h3>
                    <p class="mt-1 text-sm text-slate-400">Generate onboarding materials for new employees</p>
                </div>
                <div class="px-6 py-4">
                    <div class="mb-6">
                        <h4 class="text-sm font-medium text-slate-300 mb-3">Employee Information</h4>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="first-name" class="block text-sm font-medium text-slate-400 mb-1">First Name</label>
                                <input type="text" id="first-name" class="bg-slate-900 border border-slate-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5" placeholder="John">
                            </div>
                            <div>
                                <label for="last-name" class="block text-sm font-medium text-slate-400 mb-1">Last Name</label>
                                <input type="text" id="last-name" class="bg-slate-900 border border-slate-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5" placeholder="Doe">
                            </div>
                            <div>
                                <label for="department" class="block text-sm font-medium text-slate-400 mb-1">Department</label>
                                <select id="department" class="bg-slate-900 border border-slate-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5">
                                    <option selected>Select department</option>
                                    <option value="Engineering">Engineering</option>
                                    <option value="Marketing">Marketing</option>
                                    <option value="Sales">Sales</option>
                                    <option value="HR">Human Resources</option>
                                    <option value="Finance">Finance</option>
                                </select>
                            </div>
                            <div>
                                <label for="start-date" class="block text-sm font-medium text-slate-400 mb-1">Start Date</label>
                                <input type="date" id="start-date" class="bg-slate-900 border border-slate-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5">
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-6">
                        <h4 class="text-sm font-medium text-slate-300 mb-3">Account Setup</h4>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="upn" class="block text-sm font-medium text-slate-400 mb-1">User Principal Name</label>
                                <div class="flex">
                                    <input type="text" id="upn" class="bg-slate-900 border border-slate-700 text-white text-sm rounded-l-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5" placeholder="john.doe" value="john.doe">
                                    <span class="inline-flex items-center px-3 text-sm text-slate-400 bg-slate-700 rounded-r-lg border border-l-0 border-slate-700">@company.com</span>
                                </div>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-slate-400 mb-1">Authentication Method</label>
                                <div class="flex space-x-4">
                                    <div class="flex items-center">
                                        <input id="tap-method" name="auth-method" type="radio" checked class="h-4 w-4 text-blue-600 border-slate-700 focus:ring-blue-500 bg-slate-700">
                                        <label for="tap-method" class="ml-2 block text-sm text-slate-400">Temporary Access Pass</label>
                                    </div>
                                    <div class="flex items-center">
                                        <input id="password-method" name="auth-method" type="radio" class="h-4 w-4 text-blue-600 border-slate-700 focus:ring-blue-500 bg-slate-700">
                                        <label for="password-method" class="ml-2 block text-sm text-slate-400">Initial Password</label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-6">
                        <h4 class="text-sm font-medium text-slate-300 mb-3">Resources & Contacts</h4>
                        <div class="bg-slate-900/50 rounded-lg p-4">
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div class="flex items-start">
                                    <div class="flex-shrink-0 h-10 w-10 rounded-full bg-blue-900/20 flex items-center justify-center text-blue-400">
                                        <i data-lucide="headphones" class="h-5 w-5"></i>
                                    </div>
                                    <div class="ml-3">
                                        <p class="text-sm font-medium text-white">IT Helpdesk</p>
                                        <p class="text-sm text-slate-400">helpdesk@company.com</p>
                                        <p class="text-sm text-slate-400">+1 (555) 123-4567</p>
                                    </div>
                                </div>
                                <div class="flex items-start">
                                    <div class="flex-shrink-0 h-10 w-10 rounded-full bg-purple-900/20 flex items-center justify-center text-purple-400">
                                        <i data-lucide="users" class="h-5 w-5"></i>
                                    </div>
                                    <div class="ml-3">
                                        <p class="text-sm font-medium text-white">HR Department</p>
                                        <p class="text-sm text-slate-400">hr@company.com</p>
                                        <p class="text-sm text-slate-400">+1 (555) 987-6543</p>
                                    </div>
                                </div>
                                <div class="flex items-start">
                                    <div class="flex-shrink-0 h-10 w-10 rounded-full bg-green-900/20 flex items-center justify-center text-green-400">
                                        <i data-lucide="wifi" class="h-5 w-5"></i>
                                    </div>
                                    <div class="ml-3">
                                        <p class="text-sm font-medium text-white">Wi-Fi Access</p>
                                        <p class="text-sm text-slate-400">Network: Company-Guest</p>
                                        <p class="text-sm text-slate-400">Password: Welcome2023!</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div>
                        <h4 class="text-sm font-medium text-slate-300 mb-3">Delivery Options</h4>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="inline-flex items-center">
                                    <input type="checkbox" checked class="form-checkbox h-4 w-4 text-blue-600 border-slate-700 rounded focus:ring-blue-500 bg-slate-700">
                                    <span class="ml-2 text-sm text-slate-400">Print Welcome Pack</span>
                                </label>
                                <p class="mt-1 text-xs text-slate-500">Includes company policies, contacts, and resources</p>
                            </div>
                            <div>
                                <label class="inline-flex items-center">
                                    <input type="checkbox" checked class="form-checkbox h-4 w-4 text-blue-600 border-slate-700 rounded focus:ring-blue-500 bg-slate-700">
                                    <span class="ml-2 text-sm text-slate-400">Print Credential Slip</span>
                                </label>
                                <p class="mt-1 text-xs text-slate-500">One-time print with temporary access credentials</p>
                            </div>
                            <div>
                                <label class="inline-flex items-center">
                                    <input type="checkbox" checked class="form-checkbox h-4 w-4 text-blue-600 border-slate-700 rounded focus:ring-blue-500 bg-slate-700">
                                    <span class="ml-2 text-sm text-slate-400">Send Welcome Email</span>
                                </label>
                                <p class="mt-1 text-xs text-slate-500">Email with PDF attachments (no credentials)</p>
                            </div>
                            <div>
                                <label class="inline-flex items-center">
                                    <input type="checkbox" class="form-checkbox h-4 w-4 text-blue-600 border-slate-700 rounded focus:ring-blue-500 bg-slate-700">
                                    <span class="ml-2 text-sm text-slate-400">Create Teams Chat</span>
                                </label>
                                <p class="mt-1 text-xs text-slate-500">Initiate chat with IT contact and manager</p>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="px-6 py-4 border-t border-slate-700 flex justify-between">
                    <div class="text-sm text-slate-400">
                        <i data-lucide="info" class="h-4 w-4 inline mr-1 text-blue-400"></i>
                        Credentials will be securely printed and not stored
                    </div>
                    <div>
                        <button type="button" class="mr-3 inline-flex justify-center px-4 py-2 border border-slate-700 shadow-sm text-sm font-medium rounded-md text-white bg-slate-700 hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500" data-close-modal="welcome-modal">
                            Cancel
                        </button>
                        <button type="button" class="inline-flex justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                            Generate Welcome Pack
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(welcomeModal);
}

// Initialize modals
createModals();

// Initialize signature pads when modal is opened
let employeeSignaturePad, itSignaturePad;

function initializeSignaturePads() {
    const employeeCanvas = document.getElementById('employee-signature');
    const itCanvas = document.getElementById('it-signature');
    
    if (employeeCanvas && itCanvas) {
        employeeSignaturePad = new SignaturePad(employeeCanvas, {
            backgroundColor: 'rgba(30, 41, 59, 0)',
            penColor: '#3b82f6'
        });
        
        itSignaturePad = new SignaturePad(itCanvas, {
            backgroundColor: 'rgba(30, 41, 59, 0)',
            penColor: '#8b5cf6'
        });
        
        // Clear buttons
        document.getElementById('clear-employee').addEventListener('click', () => {
            employeeSignaturePad.clear();
        });
        
        document.getElementById('clear-it').addEventListener('click', () => {
            itSignaturePad.clear();
        });
        
        // Undo buttons
        document.getElementById('undo-employee').addEventListener('click', () => {
            const data = employeeSignaturePad.toData();
            if (data) {
                data.pop(); // remove the last dot or line
                employeeSignaturePad.fromData(data);
            }
        });
        
        document.getElementById('undo-it').addEventListener('click', () => {
            const data = itSignaturePad.toData();
            if (data) {
                data.pop(); // remove the last dot or line
                itSignaturePad.fromData(data);
            }
        });
        
        // Generate QR Code
        const qrCodeElement = document.getElementById('qr-code');
        if (qrCodeElement) {
            QRCode.toCanvas(qrCodeElement, 'https://assettrack.company.com/handover/HOV-2023-0065', {
                width: 100,
                color: {
                    dark: '#3b82f6',
                    light: '#1e293b'
                }
            }, function(error) {
                if (error) console.error(error);
            });
        }
        
        // Re-initialize Lucide icons in modal
        lucide.createIcons();
    }
}

// Modal toggles
const signingModal = document.getElementById('signing-modal');
const welcomeModal = document.getElementById('welcome-modal');

// Add click handlers to buttons that open modals
document.addEventListener('click', (e) => {
    if (e.target.closest('[data-modal="signing"]')) {
        signingModal.classList.remove('hidden');
        setTimeout(initializeSignaturePads, 100); // Small delay to ensure modal is rendered
    }
    
    if (e.target.closest('[data-modal="welcome"]')) {
        welcomeModal.classList.remove('hidden');
        lucide.createIcons();
    }
});

// Close modals when clicking outside
[signingModal, welcomeModal].forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
        }
    });
});

// Close buttons in modals
document.addEventListener('click', (e) => {
    if (e.target.closest('[data-close-modal]')) {
        const modalId = e.target.closest('[data-close-modal]').getAttribute('data-close-modal');
        document.getElementById(modalId).classList.add('hidden');
    }
});

// Add some interactive features
document.addEventListener('DOMContentLoaded', () => {
    // Add hover effects to table rows
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', () => {
            row.classList.add('bg-slate-700/50');
        });
        row.addEventListener('mouseleave', () => {
            row.classList.remove('bg-slate-700/50');
        });
    });
    
    // Add click handlers for pagination
    const paginationButtons = document.querySelectorAll('.px-3.py-1\\.5');
    paginationButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Add loading state
            button.classList.add('opacity-75');
            setTimeout(() => {
                button.classList.remove('opacity-75');
            }, 500);
        });
    });
    
    // Add notification click handler
    const notificationButton = document.querySelector('[data-lucide="bell"]').parentElement;
    notificationButton.addEventListener('click', () => {
        // Show a simple notification
        const notification = document.createElement('div');
        notification.className = 'fixed top-20 right-4 bg-blue-600 text-white px-4 py-2 rounded-md shadow-lg z-50';
        notification.textContent = 'No new notifications';
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    });
});

