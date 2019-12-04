package main

import (
	"fmt"

	pd "github.com/PagerDuty/go-pagerduty"
)

func notify(serviceKey, incidentKey, msg string) error {
	resp, err := pd.CreateEvent(pd.Event{
		Type:        "trigger",
		ServiceKey:  serviceKey,
		IncidentKey: incidentKey,
		Description: msg,
	})
	fmt.Println(resp, err)
	return err
}
