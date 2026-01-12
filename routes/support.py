"""
Support routes - Support Swaps (Micro-Assistance Requests)
"""

from flask import Blueprint, render_template, request, redirect, url_for

support_bp = Blueprint('support', __name__)

@support_bp.route('/request-help', methods=['GET', 'POST'])
def request_help():
    """Request micro-assistance from paired student."""
    if request.method == 'POST':
        # TODO: Create support request
        pass
    return render_template('support/request_help.html')

@support_bp.route('/my-requests')
def my_requests():
    """View support requests (both sent and received)."""
    # TODO: Fetch requests from database
    return render_template('support/my_requests.html')

@support_bp.route('/accept/<int:request_id>', methods=['POST'])
def accept_request(request_id):
    """Accept a support request."""
    # TODO: Update request status
    return redirect(url_for('support.my_requests'))

@support_bp.route('/decline/<int:request_id>', methods=['POST'])
def decline_request(request_id):
    """Decline a support request."""
    # TODO: Update request status
    return redirect(url_for('support.my_requests'))

@support_bp.route('/complete/<int:request_id>', methods=['POST'])
def complete_request(request_id):
    """Mark a support request as complete."""
    # TODO: Update request status, log reciprocity
    return redirect(url_for('support.my_requests'))
