package main

import (
	"fmt"

	pd "github.com/PagerDuty/go-pagerduty"
)

func notify(serviceKey, incidentKey, chain, msg string, send bool) error {
	if send {
		resp, err := pd.ManageEvent(pd.V2Event{
			RoutingKey: serviceKey,
			Action:     "trigger",
			DedupKey:   incidentKey,
			Payload: &pd.V2Payload{
				Summary:  incidentKey,
				Source:   chain,
				Severity: "critical",
				Details:  msg,
			},
		})
		fmt.Println(resp, err)
		return err
	}
	fmt.Println(msg)
	return nil
}
