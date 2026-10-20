def generate_ai_report_content(incident_facts):
    inc_id = f"TG-{incident_facts['id']}"
    transformer = incident_facts['transformer_id']
    detected_time = incident_facts['detected_time']
    threat = incident_facts['threat_level']
    response = incident_facts['owner_response']
    images = incident_facts['image_count']
    location = incident_facts['location']
    owner = incident_facts['owner_name']

    summary = (
        f"On {detected_time}, an unauthorized opening event of the transformer door on "
        f"unit {transformer} was detected at location '{location}'. The automated system "
        f"recorded the event under Incident ID {inc_id} and activated live camera "
        f"monitoring. A total of {images} still evidence images were captured during the 2-minute "
        f"recording window. System owner {owner} responded with '{response}', "
        f"classifying the event threat level as {threat}."
    )

    if threat == "HIGH":
        recommendation = (
            f"1. Dispatch an on-site physical inspection team to location '{location}' immediately.\n"
            f"2. Inspect the transformer door latch, enclosure, and electrical components for tampering.\n"
            f"3. Verify local security protocols and ensure the enclosure lock is secured."
        )
    else:
        recommendation = (
            f"1. Perform a routine physical inspection at location '{location}' when scheduled.\n"
            f"2. Check door sensor alignment and ensure the door latch is firmly closed.\n"
            f"3. Log this event as a routine verification check."
        )

    return {
        "summary": summary,
        "recommendation": recommendation
    }