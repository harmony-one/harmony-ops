package main

import (
	"fmt"

	pd "github.com/PagerDuty/go-pagerduty"
)

func notify(serviceKey, incidentKey, chain, msg string) error {
	resp, err := pd.ManageEvent(pd.V2Event{
		RoutingKey:  serviceKey,
		Action:      "trigger",
		DedupKey:    incidentKey,
		Payload:     &pd.V2Payload {
			Summary:   incidentKey,
			Source:    chain,
			Severity:  "critical",
			Details:   msg,
		},
	})
	fmt.Println(resp, err)
	return err
}
